.class public Lfixture/MemoA;
.super Ljava/lang/Object;

.method public static run()V
    .registers 1
    invoke-static {}, La/Target;->hit()V
    invoke-static/range {}, La/Target;->hit()V
    sget v0, La/Target;->value:I
    sput v0, La/Target;->value:I
    return-void
.end method
