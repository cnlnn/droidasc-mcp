package org.example.droidascfixture;

interface GenericValue<T> { T value(); }

public class MethodCases implements GenericValue<String> {
    public String choose(int value) { return "INTEGER_OVERLOAD"; }
    public String choose(String value) { return "STRING_OVERLOAD"; }
    public String value() { return "GENERIC_VALUE"; }
    public int[] arrays(String[][] input, long count) { return new int[] { 7 }; }
    public String caf\u00e9() { return "UNICODE_METHOD"; }
    public native void nativeCase();
}
