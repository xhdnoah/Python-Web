#负责逻辑处理的视图基类 
class View:
    #支持的请求方法
    methods = None

    #请求处理函数映射
    methods_meta = None

    #视图处理函数调度接口
    def dispatch_request(self,request,*args,**options):
        raise NotImplementedError

    #生成视图处理函数，参数 name 即节点名
    @classmethod #classmethod receives the class 'View' as implicit first argument 'cls'
    def get_func(cls,name):

        #定义处理函数
        def func(*args,**kwargs):
            #在处理函数内部实例化视图对象
            obj = func.view_class()

            #通过视图对象调用处理函数调用入口，返回视图处理结果
            return obj.dispatch_request(*args,**kwargs)

        #为处理函数绑定属性
        func.view_class = cls #把对象绑定为该函数的成员，在内部实例化
        func.__name__ = name #把外部的 name 参数作为自身的__name__属性值，实现函数名与节点名的绑定
        func.__doc__ = cls.__doc__
        func.__module__ = cls.__module__
        func.methods = cls.methods

        #返回函数，这样在 add_view 方法中的 add_url_rule 里的 func 参数的值就是这个类方法生成的函数，闭包的一种实现
        return func

#控制器类
class Controller:
    def __init__(self,name,url_map):
        self.url_map = url_map #存放映射关系，一个元素为 Dict 的 List
        self.name = name #控制器名字，生成节点时会用到，为了区分不同控制器下同名的视图对象

    def __name__(self):
        # 返回控制器名字
        return self.name

        