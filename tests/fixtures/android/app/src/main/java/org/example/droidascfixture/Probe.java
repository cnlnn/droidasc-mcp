package org.example.droidascfixture;

public final class Probe {
    public int visits = 0;

    public String marker() {
        visits += 1;
        return "ASC_FIXTURE_MARKER_v1";
    }

    public String describe() {
        return marker();
    }
}
