#import <Foundation/Foundation.h>
#import <UIKit/UIKit.h>

NS_ASSUME_NONNULL_BEGIN
/** Optional read-only navigation exporter; the Garmin connection lives in a separate app. */
@interface OAJunctionCompanion : NSObject
+ (instancetype)shared;
- (void)start;
- (void)presentSetupFrom:(UIViewController *)controller;
@end
NS_ASSUME_NONNULL_END
