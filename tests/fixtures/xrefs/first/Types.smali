.class public Lfixture/Types;
.super Lexternal/Base;
.implements Lexternal/Contract;

.annotation runtime Lexternal/Mark;
    value = Lfixture/Target;
    nested = .subannotation Lexternal/Nested;
        types = {Lfixture/Target;, [Lfixture/Target;}
    .end subannotation
.end annotation

.field public member:Lfixture/Target;
    .annotation runtime Lexternal/Mark;
        value = Lfixture/Target;
    .end annotation
.end field

.method public static typed(Lfixture/Target;[Lfixture/Target;)Lfixture/Target;
    .registers 3
    .param p0
        .annotation runtime Lexternal/Mark;
            value = Lfixture/Target;
        .end annotation
    .end param
    .annotation runtime Lexternal/Mark;
        value = Lfixture/Target;
    .end annotation
    const-class v0, Lfixture/Target;
    check-cast p0, Lfixture/Target;
    const-class v0, [Lfixture/Target;
    return-object p0
.end method
