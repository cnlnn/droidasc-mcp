interface InterfaceBase {}

interface InterfaceChild extends InterfaceBase {}

class HierarchyBase implements InterfaceChild {}

class HierarchyChild extends HierarchyBase {}

class HierarchyGrandchild extends HierarchyChild {}

class HierarchyDirect implements InterfaceBase {}

class LoginChild extends Login {}
