#import "OAJunctionCompanion.h"
#import "OARoutingHelper.h"
#import "OARouteCalculationResult.h"
#import "OARouteDirectionInfo.h"
#import "OAApplicationMode.h"
#import "OsmAndSharedWrapper.h"
#import <Security/Security.h>
#import <arpa/inet.h>
#import <fcntl.h>
#import <sys/socket.h>
#import <unistd.h>

static NSString *const EnabledKey = @"junctionExporterEnabled";
static NSString *const CredentialService = @"net.osmand.junction.source";
static const uint16_t JunctionPortNumber = 38765;

@interface OAJunctionCompanion () <OARouteInformationListener>
@end

@implementation OAJunctionCompanion
{
    dispatch_queue_t _geometryQueue;
    dispatch_queue_t _networkQueue;
    dispatch_source_t _listener;
    dispatch_semaphore_t _clients;
    NSMutableDictionary<NSNumber *, NSDictionary *> *_cache;
    NSMutableDictionary<NSNumber *, NSNumber *> *_cacheTimes;
    NSMutableSet<NSNumber *> *_building;
    OARouteCalculationResult *_observedRoute;
    NSString *_profile;
    NSString *_session;
    NSString *_credential;
    NSUInteger _revision;
    NSInteger _generation;
    NSInteger _sequence;
    NSInteger _currentIndex;
    BOOL _arrived;
    BOOL _started;
    BOOL _workerBusy;
    NSMutableDictionary<NSString *, NSDictionary *> *_clocks;
}

+ (instancetype)shared
{
    static OAJunctionCompanion *instance;
    static dispatch_once_t once;
    dispatch_once(&once, ^{ instance = [OAJunctionCompanion new]; });
    return instance;
}

- (instancetype)init
{
    if ((self = [super init]))
    {
        _geometryQueue = dispatch_queue_create("net.osmand.junction.geometry", DISPATCH_QUEUE_SERIAL);
        _networkQueue = dispatch_queue_create("net.osmand.junction.network", DISPATCH_QUEUE_CONCURRENT);
        _clients = dispatch_semaphore_create(4);
        _cache = [NSMutableDictionary new];
        _cacheTimes = [NSMutableDictionary new];
        _building = [NSMutableSet new];
        _clocks = [NSMutableDictionary new];
        _session = NSUUID.UUID.UUIDString;
        _currentIndex = -1;
    }
    return self;
}

- (void)start
{
    NSAssert(NSThread.isMainThread, @"Native navigation observation belongs to the main thread");
    if (_started) return;
    _started = YES;
    [[OARoutingHelper sharedInstance] addListener:self];
    NSNotificationCenter *center = NSNotificationCenter.defaultCenter;
    [center addObserver:self selector:@selector(lifecycleChanged:) name:UIApplicationDidEnterBackgroundNotification object:nil];
    [center addObserver:self selector:@selector(lifecycleChanged:) name:UIApplicationWillEnterForegroundNotification object:nil];
    if ([NSUserDefaults.standardUserDefaults boolForKey:EnabledKey]) [self enable];
}

- (void)invalidate
{
    _revision++;
    [_cache removeAllObjects];
    [_cacheTimes removeAllObjects];
    [_building removeAllObjects];
}

- (void)lifecycleChanged:(NSNotification *)notification { [self invalidate]; }
- (void)newRouteIsCalculated:(BOOL)newRoute { _arrived = NO; [self invalidate]; }
// This callback fires for ordinary point progress too. Capture observes the native
// decision index; progress alone must not discard the current/next fixed diagrams.
- (void)routeWasUpdated { }
- (void)routeWasCancelled { _arrived = NO; [self invalidate]; }
- (void)routeWasFinished { _arrived = YES; [self invalidate]; }

- (NSString *)credential
{
    if (_credential) return _credential;
    NSDictionary *query = @{(__bridge id)kSecClass: (__bridge id)kSecClassGenericPassword,
        (__bridge id)kSecAttrService: CredentialService, (__bridge id)kSecAttrAccount: @"bridge",
        (__bridge id)kSecReturnData: @YES};
    CFTypeRef result = NULL;
    OSStatus status = SecItemCopyMatching((__bridge CFDictionaryRef)query, &result);
    if (status == errSecSuccess)
    {
        _credential = [[NSString alloc] initWithData:CFBridgingRelease(result) encoding:NSUTF8StringEncoding];
        return _credential;
    }
    if (status != errSecItemNotFound) return nil;
    uint8_t bytes[32];
    if (SecRandomCopyBytes(kSecRandomDefault, sizeof(bytes), bytes) != errSecSuccess) return nil;
    NSMutableString *token = [NSMutableString new];
    for (NSUInteger i = 0; i < sizeof(bytes); i++) [token appendFormat:@"%02x", bytes[i]];
    NSMutableDictionary *item = [query mutableCopy];
    [item removeObjectForKey:(__bridge id)kSecReturnData];
    item[(__bridge id)kSecValueData] = [token dataUsingEncoding:NSUTF8StringEncoding];
    item[(__bridge id)kSecAttrAccessible] = (__bridge id)kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly;
    if (SecItemAdd((__bridge CFDictionaryRef)item, NULL) != errSecSuccess) return nil;
    _credential = token;
    return _credential;
}

- (BOOL)enable
{
    if (_listener) return YES;
    NSString *credential = [self credential];
    if (credential.length != 64) return NO;
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) return NO;
    int one = 1;
    setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &one, sizeof(one));
    struct sockaddr_in address = {0};
    address.sin_len = sizeof(address);
    address.sin_family = AF_INET;
    address.sin_port = htons(JunctionPortNumber);
    address.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    if (bind(fd, (struct sockaddr *)&address, sizeof(address)) || listen(fd, 4)) { close(fd); return NO; }
    fcntl(fd, F_SETFL, O_NONBLOCK);
    dispatch_source_t listener = dispatch_source_create(DISPATCH_SOURCE_TYPE_READ, fd, 0, _networkQueue);
    _listener = listener;
    dispatch_source_set_event_handler(listener, ^{
        int client;
        while ((client = accept(fd, NULL, NULL)) >= 0)
        {
            if (dispatch_semaphore_wait(self->_clients, DISPATCH_TIME_NOW)) { close(client); continue; }
            int accepted = client;
            dispatch_async(self->_networkQueue, ^{ [self handleClient:accepted credential:credential]; });
        }
    });
    dispatch_source_set_cancel_handler(listener, ^{ close(fd); });
    dispatch_resume(listener);
    [NSUserDefaults.standardUserDefaults setBool:YES forKey:EnabledKey];
    return YES;
}

- (void)disable
{
    [NSUserDefaults.standardUserDefaults setBool:NO forKey:EnabledKey];
    if (_listener) { dispatch_source_cancel(_listener); _listener = nil; }
    [self invalidate];
}

- (void)handleClient:(int)fd credential:(NSString *)credential
{
    int one = 1;
    setsockopt(fd, SOL_SOCKET, SO_NOSIGPIPE, &one, sizeof(one));
    struct timeval timeout = {.tv_sec = 1, .tv_usec = 0};
    setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout));
    setsockopt(fd, SOL_SOCKET, SO_SNDTIMEO, &timeout, sizeof(timeout));
    char bytes[97];
    NSUInteger count = 0;
    while (count < sizeof(bytes))
    {
        ssize_t n = recv(fd, bytes + count, sizeof(bytes) - count, 0);
        if (n <= 0) break;
        count += n;
        if (memchr(bytes, '\n', count)) break;
    }
    NSData *expected = [[@"GET " stringByAppendingFormat:@"%@\n", credential] dataUsingEncoding:NSUTF8StringEncoding];
    BOOL authenticated = count == expected.length;
    if (authenticated)
    {
        const uint8_t *a = expected.bytes;
        unsigned diff = 0;
        for (NSUInteger i = 0; i < count; i++) diff |= a[i] ^ (uint8_t)bytes[i];
        authenticated = diff == 0;
    }
    if (!authenticated) { close(fd); dispatch_semaphore_signal(_clients); return; }
    NSTimeInterval received = NSProcessInfo.processInfo.systemUptime;
    dispatch_async(dispatch_get_main_queue(), ^{
        if (!self->_listener || NSProcessInfo.processInfo.systemUptime - received > .2)
        { close(fd); dispatch_semaphore_signal(self->_clients); return; }
        NSDictionary *snapshot = [self capture];
        NSData *data = [NSJSONSerialization dataWithJSONObject:snapshot options:0 error:nil];
        dispatch_async(self->_networkQueue, ^{
            if (data.length <= 65536)
            {
                NSMutableData *wire = [data mutableCopy];
                [wire appendBytes:"\n" length:1];
                NSUInteger sent = 0;
                while (sent < wire.length)
                {
                    ssize_t n = send(fd, (const char *)wire.bytes + sent, wire.length - sent, 0);
                    if (n <= 0) break;
                    sent += n;
                }
            }
            close(fd);
            dispatch_semaphore_signal(self->_clients);
        });
    });
}

- (NSInteger)age:(CLLocation *)location key:(NSString *)key
{
    if (!location) return 60000;
    NSTimeInterval stamp = location.timestamp.timeIntervalSince1970;
    NSTimeInterval now = NSProcessInfo.processInfo.systemUptime;
    NSDictionary *previous = _clocks[key];
    if (!previous || [previous[@"stamp"] doubleValue] != stamp)
    {
        NSTimeInterval age = NSDate.date.timeIntervalSince1970 - stamp;
        if (age < -1 || !isfinite(age)) return 60000;
        previous = @{@"stamp": @(stamp), @"seen": @(now), @"age": @(MAX(0, age))};
        _clocks[key] = previous;
    }
    NSTimeInterval elapsed = now - [previous[@"seen"] doubleValue];
    return elapsed < 0 ? 60000 : MIN(60000, (NSInteger)ceil(([previous[@"age"] doubleValue] + elapsed) * 1000));
}

- (NSDictionary *)capture
{
    OARoutingHelper *helper = OARoutingHelper.sharedInstance;
    @synchronized (helper)
    {
    OARouteCalculationResult *route = [helper getRoute];
    NSString *profile = [[helper getAppMode] isDerivedRoutingFrom:OAApplicationMode.BICYCLE] ? @"bicycle" : @"motorcycle";
    if (route != _observedRoute || ![_profile isEqual:profile])
    {
        _observedRoute = route;
        _profile = profile;
        _session = NSUUID.UUID.UUIDString;
        _generation = 0;
        _sequence = 0;
        _currentIndex = -1;
        [self invalidate];
    }
    OANextDirectionInfo *next = [helper getNextRouteDirectionInfo:[OANextDirectionInfo new] toSpeak:NO];
    NSArray<OARouteDirectionInfo *> *directions = [route getImmutableAllDirections];
    NSUInteger found = next.directionInfo ? [directions indexOfObjectIdenticalTo:next.directionInfo] : NSNotFound;
    NSInteger index = found == NSNotFound ? -1 : (NSInteger)found;
    NSString *state = _arrived ? @"arrived" : [helper isRouteBeingCalculated] ? @"recalculating" :
        ([helper isPauseNavigation] || ![helper isFollowingMode] || ![route isCalculated]) ? @"idle" :
        [OARoutingHelper isDeviatedFromRoute] || index < 0 ? @"unavailable" : @"active";
    if (index != _currentIndex)
    {
        _currentIndex = index;
        _generation++;
        for (NSNumber *key in _cache.allKeys) if (key.integerValue != index && key.integerValue != index + 1)
        { [_cache removeObjectForKey:key]; [_cacheTimes removeObjectForKey:key]; }
    }
    if (![state isEqual:@"active"]) [self invalidate];
    CLLocation *fix = [helper getLastFixedLocation];
    CLLocation *projection = [helper getLastProjection];
    NSInteger fixAge = [self age:fix key:@"fix"];
    NSInteger progressAge = MAX(fixAge, [self age:projection key:@"projection"]);
    NSDictionary *geometry = [state isEqual:@"active"] ? _cache[@(index)] : nil;
    NSMutableDictionary *scene = geometry ? [geometry mutableCopy] :
        [@{@"geometryMode": @"unavailable", @"reason": [state isEqual:@"active"] ? @"loading native road context" : state,
           @"roadName": @"", @"maneuver": @"", @"radiusDm": @800, @"anchors": @[], @"paths": @[]} mutableCopy];
    NSInteger distance = 0;
    if ([state isEqual:@"active"])
    {
        OARouteDirectionInfo *direction = next.directionInfo;
        BOOL inside = [direction.turnType isRoundAbout] && direction.routeEndPointOffset > direction.routePointOffset &&
            route.currentRoute >= direction.routePointOffset && route.currentRoute <= direction.routeEndPointOffset;
        int target = inside ? direction.routeEndPointOffset : direction.routePointOffset;
        if (target >= 0 && target < [route getImmutableAllLocations].count)
            distance = MAX(0, [route getDistanceToPoint:projection locationIndex:target]);
        if (!geometry) [self requestBuild:index route:route profile:profile];
        else if (index + 1 < directions.count) [self requestBuild:index + 1 route:route profile:profile];
    }
    scene[@"version"] = @1;
    scene[@"session"] = _session;
    scene[@"generation"] = @(_generation % 1000001);
    scene[@"seq"] = @(++_sequence % 1000001);
    scene[@"state"] = state;
    scene[@"distanceM"] = @(MIN(1000000, distance));
    scene[@"sourceAgeMs"] = @0;
    scene[@"fixAgeMs"] = @(fixAge);
    if (fix && projection && [fix.timestamp isEqualToDate:projection.timestamp] && fix.speed >= 0 && isfinite(fix.speed))
    {
        scene[@"progressAgeMs"] = @(progressAge);
        scene[@"speedDmps"] = @((NSInteger)MIN(700, round(fix.speed * 10)));
    }
    return @{@"version": @1, @"capturedUptimeMs": @((long long)(NSProcessInfo.processInfo.systemUptime * 1000)), @"scene": scene};
    }
}

- (void)requestBuild:(NSInteger)index route:(OARouteCalculationResult *)route profile:(NSString *)profile
{
    NSDictionary *cached = _cache[@(index)];
    if (cached && ([cached[@"geometryMode"] isEqual:@"map_context"] ||
        NSProcessInfo.processInfo.systemUptime - [_cacheTimes[@(index)] doubleValue] < 5)) return;
    if (_workerBusy) return;
    NSArray<CLLocation *> *locations = [route getImmutableAllLocations];
    NSArray<OARouteDirectionInfo *> *directions = [route getImmutableAllDirections];
    if (index < 0 || index >= directions.count || locations.count < 2) return;
    OARouteDirectionInfo *selected = directions[index];
    NSInteger anchor = selected.routePointOffset;
    NSInteger end = [selected.turnType isRoundAbout] && selected.routeEndPointOffset > anchor ? selected.routeEndPointOffset : -1;
    if (anchor < 0 || anchor >= locations.count || end >= locations.count) return;
    NSInteger first = anchor, last = anchor;
    double approach = 0, departure = 0, atExit = -1;
    while (first > 0 && approach < 125 && anchor - first < 4999)
    { approach += [locations[first - 1] distanceFromLocation:locations[first]]; first--; }
    while (last + 1 < locations.count && (departure < 125 || last < end || (atExit >= 0 && departure - atExit < 20)) && last - anchor < 4999)
    { departure += [locations[last] distanceFromLocation:locations[last + 1]]; last++; if (last == end) atExit = departure; }
    if ((first > 0 && approach < 125) || (last + 1 < locations.count && (departure < 125 || last < end || (atExit >= 0 && departure - atExit < 20)))) return;
    NSMutableArray *points = [NSMutableArray new], *decisions = [NSMutableArray new];
    NSArray<OASRouteSegmentResult *> *segments = [route getJunctionSegmentsFrom:(int)first count:(int)(last - first + 1)];
    OASJunctionPort *compiler = [OASJunctionPort new];
    for (NSInteger i = first; i <= last; i++)
    {
        CLLocationCoordinate2D coordinate = locations[i].coordinate;
        int layer = segments.count > i - first ? [compiler layerRoad:[segments[i - first] getObject]] : -99;
        [points addObject:@[@(coordinate.latitude), @(coordinate.longitude), NSNull.null, @(layer)]];
    }
    for (NSInteger i = index; i < directions.count; i++)
    {
        OARouteDirectionInfo *d = directions[i];
        if (d.routePointOffset > last) break;
        if (decisions.count >= 2000) return;
        int nativeEnd = [d.turnType isRoundAbout] && d.routeEndPointOffset > d.routePointOffset ? d.routeEndPointOffset : -1;
        [decisions addObject:@[@(d.routePointOffset), [d.turnType toXmlString] ?: @"", d.streetName ?: @"", @(d.turnType.exitOut), @(nativeEnd)]];
    }
    NSDictionary *input = @{@"points": points, @"decisions": decisions, @"indexBase": @(first),
        @"destinationIndex": @(locations.count - 1), @"profile": profile};
    NSData *data = [NSJSONSerialization dataWithJSONObject:input options:0 error:nil];
    NSString *json = [[NSString alloc] initWithData:data encoding:NSUTF8StringEncoding];
    if (!json) return;
    NSUInteger revision = _revision;
    [_building addObject:@(index)];
    _workerBusy = YES;
    dispatch_async(_geometryQueue, ^{
        // Streams are owned only by this worker. No router or resource-manager reader is shared.
        NSMutableArray<NSString *> *files = [NSMutableArray new];
        BOOL scanTruncated = NO;
        NSArray<NSString *> *roots = @[
            NSSearchPathForDirectoriesInDomains(NSDocumentDirectory, NSUserDomainMask, YES).firstObject,
            NSSearchPathForDirectoriesInDomains(NSLibraryDirectory, NSUserDomainMask, YES).firstObject];
        NSUInteger visited = 0;
        for (NSString *root in roots)
        {
            NSDirectoryEnumerator *enumerator = [NSFileManager.defaultManager enumeratorAtURL:[NSURL fileURLWithPath:root]
                includingPropertiesForKeys:@[NSURLIsRegularFileKey, NSURLIsSymbolicLinkKey] options:NSDirectoryEnumerationSkipsHiddenFiles errorHandler:nil];
            for (NSURL *url in enumerator)
            {
                if (++visited > 10000) { scanTruncated = YES; break; }
                if (![url.pathExtension.lowercaseString isEqual:@"obf"]) continue;
                NSNumber *regular = nil, *symlink = nil;
                [url getResourceValue:&regular forKey:NSURLIsRegularFileKey error:nil];
                [url getResourceValue:&symlink forKey:NSURLIsSymbolicLinkKey error:nil];
                if (regular.boolValue && !symlink.boolValue) [files addObject:url.path];
                if (files.count > 32) break;
            }
            if (files.count > 32 || scanTruncated) break;
        }
        NSString *workerInput = json;
        if (scanTruncated)
        {
            NSMutableDictionary *limited = [input mutableCopy];
            limited[@"contextTruncated"] = @YES;
            workerInput = [[NSString alloc] initWithData:[NSJSONSerialization dataWithJSONObject:limited options:0 error:nil] encoding:NSUTF8StringEncoding];
        }
        NSString *result = [compiler compileInputJson:workerInput mapFiles:files];
        NSDictionary *geometry = [NSJSONSerialization JSONObjectWithData:[result dataUsingEncoding:NSUTF8StringEncoding] options:0 error:nil];
        dispatch_async(dispatch_get_main_queue(), ^{
            self->_workerBusy = NO;
            if (revision != self->_revision || route != self->_observedRoute || ![profile isEqual:self->_profile]) return;
            [self->_building removeObject:@(index)];
            if (geometry && (index == self->_currentIndex || index == self->_currentIndex + 1))
            {
                self->_cache[@(index)] = geometry;
                self->_cacheTimes[@(index)] = @(NSProcessInfo.processInfo.systemUptime);
            }
        });
    });
}

- (void)presentSetupFrom:(UIViewController *)controller
{
    UIAlertController *alert = [UIAlertController alertControllerWithTitle:NSLocalizedString(@"junction_title", nil)
        message:NSLocalizedString(@"junction_source_explanation", nil) preferredStyle:UIAlertControllerStyleAlert];
    BOOL enabled = _listener != nil;
    [alert addAction:[UIAlertAction actionWithTitle:NSLocalizedString(enabled ? @"junction_disable" : @"junction_enable", nil)
        style:UIAlertActionStyleDefault handler:^(UIAlertAction *action) {
            if (enabled) [self disable];
            else if (![self enable])
            {
                UIAlertController *error = [UIAlertController alertControllerWithTitle:NSLocalizedString(@"junction_title", nil)
                    message:NSLocalizedString(@"junction_source_unavailable", nil) preferredStyle:UIAlertControllerStyleAlert];
                [error addAction:[UIAlertAction actionWithTitle:NSLocalizedString(@"shared_string_ok", nil) style:UIAlertActionStyleDefault handler:nil]];
                [controller presentViewController:error animated:YES completion:nil];
            }
        }]];
    if (enabled) [alert addAction:[UIAlertAction actionWithTitle:NSLocalizedString(@"junction_connect_bridge", nil)
        style:UIAlertActionStyleDefault handler:^(UIAlertAction *action) {
            NSURL *url = [NSURL URLWithString:[@"junctionbridge://source?token=" stringByAppendingString:[self credential]]];
            [UIApplication.sharedApplication openURL:url options:@{} completionHandler:nil];
        }]];
    [alert addAction:[UIAlertAction actionWithTitle:NSLocalizedString(@"shared_string_cancel", nil) style:UIAlertActionStyleCancel handler:nil]];
    [controller presentViewController:alert animated:YES completion:nil];
}
@end
