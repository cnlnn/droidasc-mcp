.class public Lfixture/MemoB;
.super Ljava/lang/Object;

.method public static run()V
    .registers 1
    invoke-static {}, Lb/Target;->miss()V
    invoke-static/range {}, Lb/Target;->miss()V
    sget v0, Lb/Target;->other:I
    sput v0, Lb/Target;->other:I
    return-void
.end method
