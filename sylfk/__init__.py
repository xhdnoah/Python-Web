from werkzeug.serving import run_simple
from werkzeug.wrappers import Response
from sylfk.wsgi_adapter import wsgi_app
import sylfk.exceptions as exceptions
from sylfk.helper import parse_static_key
from sylfk.route import Route
from sylfk.template_engine import replace_template
from sylfk.session import create_session_id, session
import os
import json

# 定义文件类型
TYPE_MAP = {
    'css': 'text/css',
    'js': 'text/js',
    'png': 'image/png',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg'
}

# 处理函数数据结构


class ExecFunc:
    def __init__(self, func, func_type, **options):
        self.func = func  # 处理函数
        self.options = options  # 附带函数
        self.func_type = func_type  # 函数类型

# 为了低耦合度，方便模块化，需要为处理函数结构命名，实际开发先写好模块，需要替换时就直接替换与URL绑定的节点名中的模块，提高模块复用性。
# 需要三种映射关系，1.绑定URL与处理函数的节点名 2.绑定节点名与处理函数结构体也就是 ExecFunc 的实例 3.绑定静态资源文件内容与静态资源URL


class SYLFk:
    # 类属性，模版文件本地存放目录
    template_folder = None
    # 实例化方法

    def __init__(self, static_folder='static', template_folder='template', session_path=".session"):
        self.host = '127.0.0.1'  # 默认主机
        self.port = 8080  # 默认端口
        self.url_map = {}  # 存放 URL 与 Endpoint 映射
        self.static_map = {}  # 存放 URL 与 静态资源的映射
        self.function_map = {}  # 存放 Endpoint 与请求处理函数的映射
        self.static_folder = static_folder  # 静态资源本地存放路径，默认放在应用所在目录的 static 文件夹下
        self.template_folder = template_folder  # 模版文件本地存放路径，默认放在应用所在目录的 template 目录下
        # 为类的 template_folder 也初始化，供上面的置换模版引擎调用
        SYLFk.template_folder = self.template_folder
        self.route = Route(self)  # 路由装饰器
        self.session_path = session_path

    # 路由的本质就是找到 URL 对应的处理函数，负责分析请求的URL，找到对应节点名，再找到对应处理函数对象,实现URL路由追踪函数
    @exceptions.capture
    def dispatch_request(self, request):
        # 去掉 URL 中域名部分，也就是从http://xxx/com/path/file?xx=xx 中提取 path/file 这部分
        url = "/"+"/".join(request.url.split("/")[3:]).split("?")[0]

        # 通过 URL 寻找节点名
        if url.find(self.static_folder) == 1 and url.index(self.static_folder) == 1:
            # 如果 URL 以静态资源文件夹名首目录，则资源为静态资源，节点定义为 static
            endpoint = 'static'
            url = url[1:]
        else:
            # 若不以 static 为首，则从 URL 与节点的映射表中获取节点
            endpoint = self.url_map.get(url, None)

        # 定义响应报头,Server 参数的值表示运行的服务名，通常有 IIS,Apache,Tomcat,Nginx等，这里自定义为 SYL Web 0.1
        headers = {'Server': 'SYL Web 0.1'}

        # 如果节点为空，抛出页面未找到异常
        if endpoint is None:
            raise exceptions.PageNotFoundError

        # 获取节点对应的执行函数
        exec_function = self.function_map[endpoint]

        # 判断执行函数类型
        if exec_function.func_type == 'route':
            """ 路由处理 """

            # 判断请求方法是否支持
            if request.method in exec_function.options.get('methods'):
                """ 路由处理结果 """

                # 判断路由的执行函数是否需要请求体进行内部处理
                argcount = exec_function.func.__code__.co_argcount

                if argcount > 0:
                    # 需要附带请求体进行结果处理
                    rep = exec_function.func(request)
                else:
                    # 不需要附带请求体进行结果处理
                    rep = exec_function.func()
            else:
                """未知请求方法"""

                # 抛出请求方法不支持异常
                return exceptions.InvalidRequestMethodError

        elif exec_function.func_type == 'view':
            """视图处理逻辑"""

            # 所有视图处理函数都需要附带请求体来获取处理结果
            rep = exec_function.func(request)
        elif exec_function.func_type == 'static':
            """静态逻辑处理"""

            # 静态资源返回的是一个预先封装好的响应体，所以直接返回
            return exec_function.func(url)
        else:
            """未知类型处理"""

            # 抛出未知处理类型异常
            raise exceptions.UnknownFuncError

        # 定义 200 状态码表示成功
        status = 200
        # 定义响应体类型
        content_type = 'text/html'
        # 从请求中取出 Cookie
        cookies = request.cookies

        # 如果 session_id 这个键不在cookies中，则通知客户端设置 Cookie
        if 'session_id' not in cookies:
            headers = {
                # 定义 Set-Cookie属性，通知客户端 Cookie，create_session_id 是生成一个无规律唯一字符串的方法
                'Set-Cookie': 'session_id=%s' % create_session_id(),
                'Sever': 'Shiyanlou Framework'  # 定义响应报头的 Server 属性
            }
        else:
            # 定义响应报头的 Server 属性
            headers = {
                'Server': 'Shiyanlou Framework'
            }

        # 判断如果返回值是一个 Response 类型，则直接返回而不是走到最后再封装一个 Response
        if isinstance(rep, Response):
            return rep

        # 返回响应体
        return Response(rep, content_type='%s;charset=UTF-8' % content_type, headers=headers, status=status)

    # 启动入口
    def run(self, host=None, port=None, **options):
        # 如果有参数进来且值不为空，则赋值
        for key, value in options.items():
            if value is not None:
                self.__setattr__(key, value)

        # 映射静态资源处理函数，所有静态资源处理函数都是静态资源路由
        self.function_map['static'] = ExecFunc(
            func=self.dispatch_static, func_type='static')

        # 如果会话记录存放目录不存在，则创建它
        if not os.path.exists(self.session_path):
            os.mkdir(self.session_path)

        # 设置会话记录存放目录
        session.set_storage_path(self.session_path)

        # 加载本地缓存的 session 记录
        session.load_local_session()

        # 如果 host 不为 None，替换 self.host
        if host:
            self.host = host

        # 如果 port 不为 None，替换 self.port
        if port:
            self.port = port
        # 把框架本身也就是应用本身和其它几个配置参数传给 werkzeug 的 run_simple
        run_simple(hostname=self.host, port=self.port,
                   application=self, **options)

    # 框架被 WSGI 调用入口的方法
    def __call__(self, environ, start_response):
        return wsgi_app(self, environ, start_response)

    
    # 添加路由规则
    @exceptions.capture
    def add_url_rule(self, url, func, func_type, endpoint=None, **options):

        # 如果节点未命名，使用处理函数的名字
        if endpoint is None:
            endpoint = func.__name__

        # 抛出 URL 已存在异常
        if url in self.url_map:
            raise exceptions.URLExistsError

        # 如果类型不是静态资源，且节点已经存在，则抛出节点已存在异常
        if endpoint in self.function_map and func_type != 'static':
            raise exceptions.EndpointExistsError

        # 添加 URL 与节点映射
        self.url_map[url] = endpoint

        # 添加节点与请求处理函数映射
        self.function_map[endpoint] = ExecFunc(func, func_type, **options)


    # 静态资源调路由，用来选招匹配的 URL 并返回对应类型和文件内容封装成的响应体
    @exceptions.capture
    def dispatch_static(self, static_path):
        # 判断资源文件是否在静态资源规则中，如果不存在返回404
        if os.path.exists(static_path):
            # 获取资源文件后缀
            key = parse_static_key(static_path)

            # 获取文件类型
            doc_type = TYPE_MAP.get(key, 'text/plain')

            # 获取文件内容
            with open(static_path, 'rb') as f:
                rep = f.fead()

            # 封装并返回响应体
            return Response(rep, content_type=doc_type)
        else:
            # 抛出页面未找到异常
            raise exceptions.PageNotFoundError

    # 添加视图规则
    def bind_view(self, url, view_class, endpoint):
        self.add_url_rule(url, func=view_class.get_func(
            endpoint), func_type='view')  # 视图通过实现 add_url_rule 接口把规则绑定到框架

    # 控制器加载
    def load_controller(self, controller):

        # 获取控制器名字
        name = controller.__name__()

        # 遍历控制器的`url_map`成员，就是一个List对象，每一个成员都是拥有 url,view,endpoint三个key的Dict，再把每一个Dict通过bind_view绑定到url_map
        for rule in controller.url_map:
            # 绑定 URL 与视图对象，最后的节点名格式为`控制器名`+"."+定义的节点名
            self.bind_view(rule['url'], rule['view'],
                           name+'.'+rule['endpoint'])

# URL 重定向方法


def redirect(url, status_code=302):
    # 定义一个响应体
    response = Response('', status=status_code)

    # 为响应体的报头中的 Location 参数与 URL 进行绑定 ，通知客户端自动跳转
    response.headers['Location'] = url

    # 返回响应体
    return response

# 模版引擎接口


def simple_template(path, **options):
    return replace_template(SYLFk, path, **options)

# 封装 JSON 数据响应包


def render_json(data):
    # 定义默认文件类型为纯文本
    content_type = "text/plain"

    # 如果是 Dict 或者 List 类型，则开始转换为 JSON 格式数据
    if isinstance(data, dict) or isinstance(data, list):

        # 将 data 转换为 JSON 数据格式
        data = json.dumps(data)

        # 定义文件类型为 JSON 格式
        content_type = "application/json"

    # 返回封装完的响应体
    return Response(data, content_type="%s; charset = UTF-8" % content_type, status=200)

# 返回让客户端保存文件到本地的响应体

@exceptions.capture
def render_file(file_path, file_name=None):

    # 判断服务器是否有该文件
    if os.path.exists(file_path):

        # 判断服务器是否有该文件，抛出文件不存在异常
        if os.path.exists(file_path):

            # 判断是否有读取权限，没有则抛出权限不足异常
            if not os.access(file_path,os.R_OK):
                raise exceptions.RequireReadPermissionError

        # 读取文件内容
        with open(file_path, "rb") as f:
            content = f.read()

        # 如果没有设置文件名，则以 “/” 分割路径取最后一项最为文件名
        if file_name is None:
            file_name = file_path.split("/")[-1]

        # 封装响应报头，指定为附件类型，并定义下载的文件名
        headers = {
            'Content=Disposition': 'attachment; filename="%s"' % file_name
        }

        # 返回响应体
        return Response(content, headers=headers, status=200)

    # 如果不存在该文件，抛出文件不存在异常
    return exceptions.FileNotExistsError
