from sylfk import SYLFk, simple_template, redirect, render_json, render_file
from sylfk.session import session
from sylfk.view import Controller
from core.base_view import BaseView, SessionView
from sylfk import redirect
from core.database import dbconn
from sylfk.dbconnector import BaseDB,DBResult

# 首页视图


class Index(SessionView):
    def get(self, request):
        # 获取当前会话中的 user 的值
        user = session.get(request, 'user')

        # 把 user 的值用模版引擎置换到页面中并返回
        return simple_template("index.html", user=user, message="实验楼，你好")

# 登录视图


class Login(BaseView):
    def get(self, request):
        # 从 GET 请求中获取 state 参数，如果不存在则返回用默认值 1
        state = request.args.get('state', "1")

        # 通过模版返回给用户一个登录页面，当 state 不为 1 时，页面信息返回用户名错误或不存在
        return simple_template("layout.html", title="登录",message="输入登录用户名" if state == "1" else "用户名错误或不存在，重新输入")

    def post(self, request):
        # 把用户提交的信息到数据库中进行查询
        ret = dbconn.execute(
            '''SELECT * FROM user WHERE f_name = %(user)s''', request.form)

        # 如果有匹配的结果，说明注册过，反之再次重定向回登录页面，并附带 state=0 过去，通知页面提示登录错误信息
        if ret.rows == 1:
            # 如果有匹配，获取第一条数据的 f_name 字段作为用户名
            user = ret.get_first()['f_name']

            # 把用户名放到 Session 中
            session.push(request, 'user', user)

            # Session 已经可以验证通过，所以重定向到首页
            return redirect("/")
        return redirect("/login?state=0")

# 登出视图


class Logout(SessionView):
    def get(self, request):
        # 从当前会话中删除 user
        session.pop(request, 'user')

        # 返回登出成功提示和首页链接
        return redirect("/")


class API(BaseView):
    def get(self, request):
        data = {
            'name': 'shiyanlou_001',
            'company': '实验楼',
            'department': '课程部'
        }
        return render_json(data)


class Download(BaseView):
    def get(self, request):
        return render_file("main.py")


class Register(BaseView):
    def get(self, request):
        # 收到 GET 请求时通过模版返回一个注册页面
        return simple_template("layout.html", title="注册",message="输入注册用户名")

    def post(self, request):
        # 把用户提交的信息作为参数，执行 SQL 的 INSERT 语句把信息保存到数据库的表中，我这里就是 shiyanlou 数据库中的 user 表里
        ret = dbconn.insert(
            'INSERT INTO user(f_name) VALUES(%(user)s)', request.form)
        # 如果添加成功，则表示注册成功，重定向到登录页面
        if ret.suc:
            return redirect("/login")
        else:
            # 添加失败的话，把错误信息返回方便调试
            return render_json(ret.to_dict())



syl_url_map = [
    {
        'url': '/',
        'view': Index,
        'endpoint': 'index'
    },
    {
        'url': '/register',
        'view': Register,
        'endpoint': 'register'
    },
    {
        'url': '/login',
        'view': Login,
        'endpoint': 'test'
    },
    {
        'url': '/logout',
        'view': Logout,
        'endpoint': 'logout'
    },
    {
        'url': '/api',
        'view': API,
        'endpoint': 'api'
    },
    {
        'url': '/download',
        'view': Download,
        'endpoint': 'download'
    }
]

app = SYLFk()

index_controller = Controller('index', syl_url_map)
app.load_controller(index_controller)

app.run()
