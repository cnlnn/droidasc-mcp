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

.method public static eSwitches(I)I
    .registers 2
    packed-switch p0, :packed
    sparse-switch p0, :sparse
    const-wide/16 v0, 0x60
    const v0, 0x600000
    return v0
    :selected
    const/4 v0, 0x1
    return v0
    :packed
    .packed-switch 0x1
        :selected
    .end packed-switch
    :sparse
    .sparse-switch
        0x6000 -> :selected
    .end sparse-switch
.end method
