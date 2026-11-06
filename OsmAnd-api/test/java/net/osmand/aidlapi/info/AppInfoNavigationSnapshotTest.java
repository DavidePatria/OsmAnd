package net.osmand.aidlapi.info;

import android.os.Bundle;
import android.os.Parcel;
import net.osmand.aidlapi.AidlParams;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.annotation.Config;
import static org.junit.Assert.*;

@RunWith(RobolectricTestRunner.class)
@Config(sdk={24,36},manifest=Config.NONE)
public class AppInfoNavigationSnapshotTest {
    private AppInfoParams info() {
        Bundle turn=new Bundle();turn.putInt("turnType",3);
        return new AppInfoParams(null,null,turn,11,120,1234,true);
    }
    private Parcel written(AidlParams model) {
        Parcel parcel=Parcel.obtain();model.writeToParcel(parcel,0);parcel.setDataPosition(0);return parcel;
    }
    @Test public void currentModelRoundTripsOptionalSnapshotAndOldFields() {
        AppInfoParams before=info();Bundle snapshot=new Bundle();snapshot.putInt("version",1);snapshot.putString("sceneJson","{\"version\":1}");
        before.setNavigationSnapshot(snapshot);Parcel parcel=written(before);
        try {
            AppInfoParams after=AppInfoParams.CREATOR.createFromParcel(parcel);
            assertEquals(1,after.getNavigationSnapshot().getInt("version"));assertEquals(snapshot.getString("sceneJson"),after.getNavigationSnapshot().getString("sceneJson"));
            assertEquals(11,after.getLeftTime());assertEquals(120,after.getLeftDistance());assertEquals(1234,after.getArrivalTime());
            assertEquals(3,after.getTurnInfo().getInt("turnType"));assertTrue(after.isMapVisible());
        } finally { parcel.recycle(); }
    }
    @Test public void oldWriterNewReaderHasNoSnapshot() {
        Legacy legacy=new Legacy();legacy.distance=42;Parcel parcel=written(legacy);
        try { AppInfoParams after=new AppInfoParams(parcel);assertEquals(42,after.getLeftDistance());assertNull(after.getNavigationSnapshot()); }
        finally { parcel.recycle(); }
    }
    @Test public void newWriterOldReaderIgnoresAdditionalBundle() {
        AppInfoParams before=info();Bundle snapshot=new Bundle();snapshot.putInt("version",1);before.setNavigationSnapshot(snapshot);
        Parcel parcel=written(before);
        try { Legacy after=new Legacy();after.readFromParcel(parcel);assertEquals(120,after.distance);assertEquals(3,after.turn.getInt("turnType")); }
        finally { parcel.recycle(); }
    }
    @Test public void absentFieldClearsPreviouslyReadSnapshotAndWrapperIsOwned() {
        AppInfoParams value=info();Bundle snapshot=new Bundle();snapshot.putInt("version",1);value.setNavigationSnapshot(snapshot);
        snapshot.putInt("version",2);assertEquals(1,value.getNavigationSnapshot().getInt("version"));
        value.getNavigationSnapshot().putInt("version",3);assertEquals(1,value.getNavigationSnapshot().getInt("version"));
        Parcel parcel=written(new Legacy());
        try { value.readFromParcel(parcel);assertNull(value.getNavigationSnapshot()); }
        finally { parcel.recycle(); }
    }
    /** Frozen old Bundle contract; it has no knowledge of navigationSnapshot. */
    private static final class Legacy extends AidlParams {
        int distance;
        Bundle turn;
        @Override protected void writeToBundle(Bundle out) { out.putInt("leftDistance",distance); }
        @Override protected void readFromBundle(Bundle in) { distance=in.getInt("leftDistance");turn=in.getBundle("turnInfo"); }
    }
}
