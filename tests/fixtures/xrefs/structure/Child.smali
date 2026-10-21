.class public Lstructure/Child;
.super Lstructure/Base;

.method public static call()Ljava/lang/String;
    .registers 1
    invoke-static {}, Lstructure/Base;->text()Ljava/lang/String;
    move-result-object v0
    return-object v0
.end method
