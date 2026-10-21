.class public Lfixture/Boundary;
.super Ljava/lang/Object;

.field public static value:I

.method public static aNoReference()V
    .registers 1
    return-void
.end method

.method public static bLargeFrame()V
    .registers 96
    return-void
.end method

.method public static cPayload()[S
    .registers 1
    const/4 v0, 0x2
    new-array v0, v0, [S
    fill-array-data v0, :data
    return-object v0
    :data
    .array-data 2
        0x0060s
        0x0000s
    .end array-data
.end method

.method public static dReal()I
    .registers 1
    sget v0, Lfixture/Boundary;->value:I
    return v0
.end method
