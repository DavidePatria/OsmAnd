#import <Foundation/Foundation.h>

NS_ASSUME_NONNULL_BEGIN
/** Thin SDK boundary; all state changes and blocks are delivered on the main queue. */
@interface GarminLink : NSObject
@property(nonatomic, copy, nullable) void (^onDevices)(NSArray<NSDictionary *> *devices);
@property(nonatomic, copy, nullable) void (^onState)(NSString *state, BOOL ready);
@property(nonatomic, copy, nullable) void (^onMessage)(NSDictionary *message);
- (void)initializeSDK;
- (void)chooseDevices;
- (BOOL)handleURL:(NSURL *)url NS_SWIFT_NAME(handle(url:));
- (void)startWithDeviceID:(NSString *)identifier dataField:(BOOL)dataField NS_SWIFT_NAME(start(deviceID:dataField:));
- (void)stop;
- (void)send:(NSString *)message completion:(void (^)(BOOL success))completion;
- (void)openWatchApp;
@end
NS_ASSUME_NONNULL_END
