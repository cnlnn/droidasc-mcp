.class public Loracle/Caller;
.super Ljava/lang/Object;

.method public static root(Ljava/lang/invoke/MethodHandle;)V
    .registers 3
    move-object v0, p0
    const/4 v1, 0x1
    invoke-polymorphic {v0, v1}, Ljava/lang/invoke/MethodHandle;->invokeExact([Ljava/lang/Object;)Ljava/lang/Object;, (I)I
    invoke-polymorphic/range {v0 .. v1}, Ljava/lang/invoke/MethodHandle;->invokeExact([Ljava/lang/Object;)Ljava/lang/Object;, (I)I
    return-void
.end method
