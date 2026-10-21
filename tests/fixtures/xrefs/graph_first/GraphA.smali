.class public Lgraph/A;
.super Ljava/lang/Object;

.method public static root()V
    .registers 1
    const/4 v0, 0x0
    invoke-static {v0}, Lgraph/B;->step(I)V
    invoke-static {v0}, Lgraph/B;->step(I)V
    const-string v0, "overload"
    invoke-static {v0}, Lgraph/B;->step(Ljava/lang/String;)V
    invoke-static {}, Lexternal/Missing;->absent()V
    const/4 v0, 0x0
    invoke-static {v0}, Lgraph/A;->dynamic(Ljava/lang/invoke/MethodHandle;)V
    return-void
.end method

.method public static loop()V
    .registers 0
    invoke-static {}, Lgraph/A;->root()V
    return-void
.end method

.method public static entry()V
    .registers 0
    invoke-static {}, Lgraph/A;->root()V
    return-void
.end method

.method public static dynamic(Ljava/lang/invoke/MethodHandle;)V
    .registers 2
    const/4 v0, 0x1
    invoke-polymorphic {p0, v0}, Ljava/lang/invoke/MethodHandle;->invokeExact([Ljava/lang/Object;)Ljava/lang/Object;, (I)I
    return-void
.end method

.method public native noCode()V
.end method

.method public static recursive()V
    .registers 0
    invoke-static {}, Lgraph/A;->recursive()V
    return-void
.end method

.method public static custom()V
    .registers 0
    invoke-custom {}, site("go", ()V)@Lexternal/Bootstrap;->link(Ljava/lang/invoke/MethodHandles$Lookup;Ljava/lang/String;Ljava/lang/invoke/MethodType;)Ljava/lang/invoke/CallSite;
    return-void
.end method
