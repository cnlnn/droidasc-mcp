.class public Lstructure/Base;
.super Lexternal/Root;
.implements Lstructure/Contract;

.field public static counter:I
.field private label:Ljava/lang/String;

.method public static text()Ljava/lang/String;
    .registers 1
    const-string v0, "MixedCase \u4e2d\u6587"
    return-object v0
.end method

.method public static text(I)Ljava/lang/String;
    .registers 2
    const-string/jumbo v0, ""
    return-object v0
.end method

.method public static numeric()I
    .registers 1
    const/16 v0, 0x1234
    return v0
.end method

.method public native empty()V
.end method
