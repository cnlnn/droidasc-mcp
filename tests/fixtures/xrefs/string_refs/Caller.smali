.class public Lstringrefs/Caller;
.super Ljava/lang/Object;

.field public static final poolOnly:Ljava/lang/String; = "pool-only[never]"

.method public static first()V
    .registers 1
    const-string v0, "https://example.test/a[b]?x=1.*"
    const-string/jumbo v0, "https://example.test/a[b]?x=1.*"
    const-string v0, "https://exampleXtest/ab?x=1ZZ"
    const-string v0, "MixedCase \u4e2d\u6587"
    return-void
.end method

.method public static second()V
    .registers 1
    const-string v0, "prefix https://example.test/a[b]?x=1.* suffix"
    const-string/jumbo v0, "MixedCase \u4e2d\u6587"
    const-string v0, ""
    return-void
.end method

.method public abstract absent()V
.end method
