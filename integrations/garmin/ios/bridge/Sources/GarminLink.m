#import "GarminLink.h"
#import <ConnectIQ/ConnectIQ.h>
#import <UIKit/UIKit.h>

@interface GarminLink () <IQDeviceEventDelegate, IQAppMessageDelegate, IQUIOverrideDelegate>
@end

@implementation GarminLink
{
    ConnectIQ *_sdk;
    NSArray<IQDevice *> *_devices;
    IQApp *_app;
    BOOL _ready;
    BOOL _field;
}

- (void)state:(NSString *)state ready:(BOOL)ready
{
    dispatch_async(dispatch_get_main_queue(), ^{ if (self.onState) self.onState(state, ready); });
}

- (void)publishDevices
{
    NSMutableArray *list = [NSMutableArray new];
    for (IQDevice *device in _devices)
        [list addObject:@{@"id": device.uuid.UUIDString, @"name": device.friendlyName ?: device.modelName ?: @""}];
    if (self.onDevices) self.onDevices(list);
}

- (void)initializeSDK
{
    if (_sdk) return;
    _sdk = ConnectIQ.sharedInstance;
    [_sdk initializeWithUrlScheme:@"junctionbridge" uiOverrideDelegate:self
        stateRestorationIdentifier:@"net.osmand.junction.bridge.bluetooth"];
    NSData *stored = [NSUserDefaults.standardUserDefaults dataForKey:@"authorizedGarminDevices"];
    if (stored)
    {
        NSSet *classes = [NSSet setWithObjects:NSArray.class, IQDevice.class, NSUUID.class, NSString.class, nil];
        _devices = [NSKeyedUnarchiver unarchivedObjectOfClasses:classes fromData:stored error:nil];
    }
    if (!_devices) _devices = @[];
    [self publishDevices];
}

- (void)needsToInstallConnectMobile { [self state:@"garmin_install" ready:NO]; }

- (void)chooseDevices
{
    [self initializeSDK];
    if (UIApplication.sharedApplication.applicationState == UIApplicationStateActive)
        [_sdk showConnectIQDeviceSelection];
}

- (BOOL)handleURL:(NSURL *)url
{
    if (![url.scheme.lowercaseString isEqual:@"junctionbridge"] || [url.host isEqual:@"source"]) return NO;
    [self initializeSDK];
    NSArray *devices = [_sdk parseDeviceSelectionResponseFromURL:url];
    if (!devices) return NO;
    [self stop];
    _devices = devices;
    NSData *data = [NSKeyedArchiver archivedDataWithRootObject:devices requiringSecureCoding:YES error:nil];
    if (data) [NSUserDefaults.standardUserDefaults setObject:data forKey:@"authorizedGarminDevices"];
    [self publishDevices];
    return YES;
}

- (void)startWithDeviceID:(NSString *)identifier dataField:(BOOL)dataField
{
    [self initializeSDK];
    [self stop];
    IQDevice *selected = nil;
    for (IQDevice *device in _devices) if ([device.uuid.UUIDString isEqual:identifier]) selected = device;
    if (!selected) { [self state:@"choose_watch" ready:NO]; return; }
    _field = dataField;
    NSString *appID = dataField ? @"5ee36e99-bc89-44a2-b026-040cd9e77f35" : @"9d7c2b1a-4f6e-4b3a-9c1d-2e8f5a6b7c8d";
    NSUUID *uuid = [[NSUUID alloc] initWithUUIDString:appID];
    _app = [IQApp appWithUUID:uuid storeUuid:uuid device:selected];
    [_sdk registerForDeviceEvents:selected delegate:self];
    [_sdk registerForAppMessages:_app delegate:self];
    [self state:@"waiting_watch" ready:NO];
}

- (void)stop
{
    _ready = NO;
    if (_app)
    {
        [_sdk unregisterForAppMessages:_app delegate:self];
        [_sdk unregisterForDeviceEvents:_app.device delegate:self];
    }
    _app = nil;
}

- (void)deviceStatusChanged:(IQDevice *)device status:(IQDeviceStatus)status
{
    dispatch_async(dispatch_get_main_queue(), ^{
        if (![device.uuid isEqual:self->_app.device.uuid]) return;
        // Connected precedes service discovery. Never send or prompt on that callback alone.
        self->_ready = NO;
        [self state:@"waiting_watch" ready:NO];
    });
}

- (void)deviceCharacteristicsDiscovered:(IQDevice *)device
{
    dispatch_async(dispatch_get_main_queue(), ^{
        if (![device.uuid isEqual:self->_app.device.uuid]) return;
        self->_ready = YES;
        [self state:@"watch_connected" ready:YES];
    });
}

- (void)receivedMessage:(id)message fromApp:(IQApp *)app
{
    dispatch_async(dispatch_get_main_queue(), ^{
        if (!self->_ready || ![app.uuid isEqual:self->_app.uuid] || ![app.device.uuid isEqual:self->_app.device.uuid]) return;
        if ([message isKindOfClass:NSDictionary.class] && self.onMessage) self.onMessage(message);
    });
}

- (void)send:(NSDictionary *)message completion:(void (^)(BOOL))completion
{
    if (!_ready || !_app) { completion(NO); return; }
    [_sdk sendMessage:message toApp:_app progress:nil completion:^(IQSendMessageResult result) {
        dispatch_async(dispatch_get_main_queue(), ^{ completion(result == IQSendMessageResult_Success); });
    }];
}

- (void)openWatchApp
{
    if (!_ready || !_app || _field || UIApplication.sharedApplication.applicationState != UIApplicationStateActive) return;
    [_sdk openAppRequest:_app completion:^(IQSendMessageResult result) {
        [self state:result == IQSendMessageResult_Success ? @"watch_prompt" : @"open_watch_manually" ready:self->_ready];
    }];
}
@end
