from sylfk.view import View
from sylfk.session import AuthSession, session
from sylfk import redirect

class BaseView(View): #作为应用开发时的底层库，通过 BaseView,之后每次开发只需继承它，再实现对应的 get,post方法
    #定义支持的请求方法，默认支持 GET 和 POST 方法
    methods = ['GET,POST']

    #POST 请求处理函数
    def post(self,request,*args,**options):
        pass

    #GET 请求处理函数
    def get(self,request,*args,**options):
        pass
    
    #视图处理函数调度入口
    def dispatch_request(self,request,*args,**options):
        #定义请求方法与处理函数的映射
        methods_meta = {
            'GET':self.get,
            'POST':self.post,
        }

        #判断该视图是支持所请求的方法，如果支持则返回对应处理函数的结果，反之返回错误提示
        if request.method in methods_meta:
            return methods_meta[request.method](request,*args,**options)
        else:
            return '<h1>Unknown or unsupported require method</h1>'

#登录验证类
class AuthLogin(AuthSession):

    #如果没有验证通过，则返回一个链接点击到登录页面
    @staticmethod
    def auth_fail_callback(request,*args,**options):
        return redirect("/login")

    #验证逻辑，如果 user 这个键不在会话当中，则验证失败，反之则成功
    @staticmethod
    def auth_logic(request,*args,**options):
        if 'user' in session.map(request):
            return True
        return False

#会话视图基类
class SessionView(BaseView):

    #验证类抓装饰器
    @AuthLogin.auth_session
    def dispatch_request(self,request,*args,**options):
        #结合装饰器内部的逻辑，调用继承的子类的 dispatch_request 方法
        return super(SessionView,self).dispatch_request(request,*args,**options)

