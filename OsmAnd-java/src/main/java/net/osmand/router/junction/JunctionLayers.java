package net.osmand.router.junction;

/** Cartographic drawing order, not elevation or a routing/connectivity decision. */
public final class JunctionLayers {
    private JunctionLayers() { }
    public static int level(String layer,String bridge,String tunnel) {
        if (layer!=null) {
            int value;
            try { value=Integer.parseInt(layer.trim()); }
            catch (NumberFormatException error) { throw new IllegalArgumentException("Unsupported road layer",error); }
            if (value < -10 || value > 10) throw new IllegalArgumentException("Unsupported road layer range");
            return value;
        }
        if (present(bridge)) return 1;
        // A building passage alone does not place this road below other ROADS.
        if (present(tunnel) && !"building_passage".equals(tunnel)) return -1;
        return 0;
    }
    private static boolean present(String value) { return value!=null && !value.equals("no") && !value.equals("false") && !value.equals("0"); }
}
