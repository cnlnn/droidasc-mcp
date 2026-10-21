.class public Lstructure/Payload;
.super Ljava/lang/Object;

.method public static select(I)I
    .registers 2
    packed-switch p0, :table
    const/4 v0, -0x1
    return v0
    :first
    const/4 v0, 0x1
    return v0
    :table
    .packed-switch 0x1
        :first
    .end packed-switch
.end method

.method public static array()[I
    .registers 2
    const/4 v0, 0x2
    new-array v0, v0, [I
    fill-array-data v0, :data
    return-object v0
    :data
    .array-data 4
        0x12345678
        0x76543210
    .end array-data
.end method
