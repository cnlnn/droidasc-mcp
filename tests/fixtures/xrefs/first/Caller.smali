.class public Lfixture/Caller;
.super Ljava/lang/Object;
.source "Caller.java"

.method public static run()V
    .registers 1
    .line 17
    const/4 v0, 0x1
    invoke-static {v0}, Lfixture/Target;->pick(I)V
    const-string v0, "STRING_ARGUMENT"
    invoke-static {v0}, Lfixture/Target;->pick(Ljava/lang/String;)V
    invoke-static {}, Lexternal/Missing;->absent()V
    return-void
.end method

.method public static dynamic(Ljava/lang/invoke/MethodHandle;)V
    .registers 2
    const/4 v0, 0x1
    invoke-polymorphic {p0, v0}, Ljava/lang/invoke/MethodHandle;->invokeExact([Ljava/lang/Object;)Ljava/lang/Object;, (I)I
    return-void
.end method

.method public static guarded()V
    .registers 1
    :try_start
    invoke-static {}, Lexternal/Missing;->absent()V
    :try_end
    return-void
    :handler
    move-exception v0
    return-void
    .catch Ljava/lang/Exception; {:try_start .. :try_end} :handler
.end method

.method public native noCode(JLjava/lang/String;)V
.end method
