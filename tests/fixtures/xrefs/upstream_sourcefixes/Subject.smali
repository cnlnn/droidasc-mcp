.class public Lsourcefixes/Subject;
.super Ljava/lang/Object;
.source "Subject.java"

.field public label:Ljava/lang/String;

.method public constructor <init>()V
    .registers 1
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V
    return-void
.end method

.method public static mayThrow()V
    .registers 0
    .annotation system Ldalvik/annotation/Throws;
        value = {Ljava/lang/Exception;}
    .end annotation
    return-void
.end method

.method public static echo(Ljava/lang/Boolean;)Ljava/lang/Boolean;
    .registers 1
    return-object p0
.end method

.method public static makeArray(I)[Ljava/lang/Object;
    .registers 2
    new-array v0, p0, [Ljava/lang/Object;
    return-object v0
.end method

.method public callSuper()Ljava/lang/String;
    .registers 2
    invoke-super {p0}, Ljava/lang/Object;->toString()Ljava/lang/String;
    move-result-object v0
    return-object v0
.end method
