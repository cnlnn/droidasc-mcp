public final class Login {
    public static int visits = 0;

    public static String marker() {
        visits++;
        return "LOGIN_NAME_MARKER";
    }

    public static String describe() {
        return marker();
    }
}
