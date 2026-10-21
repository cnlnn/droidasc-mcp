.class public Lreview/C;
.super Ljava/lang/Object;

.field public keep:I
.field public removed:Ljava/lang/String;

.method public static keep()I
    .registers 1
    const/4 v0, 0x1
    return v0
.end method

.method public static removed()V
    .registers 0
    return-void
.end method

.method public static candidates()V
    .registers 1
    const-string v0, "AKIA0000000000000000"
    const-string v0, "client_secret=synthetic_example_value_12345"
    const-string v0, "-----BEGIN PRIVATE KEY-----"
    return-void
.end method
