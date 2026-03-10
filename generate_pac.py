import urllib.request
import base64
import re

def fetch_gfwlist():
    url = 'https://raw.githubusercontent.com/gfwlist/gfwlist/master/gfwlist.txt'
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as response:
        return base64.b64decode(response.read()).decode('utf-8')

def parse_gfwlist(content):
    direct_domains = set()
    proxy_domains = set()

    for line in content.splitlines():
        line = line.strip()
        # 忽略注释和空行
        if not line or line.startswith('!') or line.startswith('['):
            continue
        # 忽略正则表达式（PAC脚本中不适用）
        if line.startswith('/') and line.endswith('/'):
            continue

        is_direct = False
        if line.startswith('@@'):
            is_direct = True
            line = line[2:] # 移除 @@ 前缀

        # 剥离 Adblock Plus 语法前缀，提取纯域名
        line = re.sub(r'^\|\|?', '', line)
        line = re.sub(r'^\.', '', line)
        line = re.sub(r'^https?://', '', line)

        # 剥离路径和端口，保留核心域名
        domain = line.split('/')[0].split(':')[0].replace('*', '')

        # 基础校验：确保是一个合法的域名结构
        if not domain or '.' not in domain or re.search(r'[^a-zA-Z0-9.-]', domain):
            continue

        if is_direct:
            direct_domains.add(domain)
        else:
            proxy_domains.add(domain)

    # 排序使输出的 PAC 文件更稳定且易于 Git 追踪差异
    return sorted(list(direct_domains)), sorted(list(proxy_domains))

def format_js_array(items):
    if not items:
        return "        []"
    lines = ["        ["]
    for i, item in enumerate(items):
        comma = "," if i < len(items) - 1 else ""
        lines.append(f'            "{item}"{comma}')
    lines.append("        ]")
    return "\n".join(lines)

def generate_pac(direct_domains, proxy_domains):
    template_start = """var proxy = '__PROXY__';
var rules = [
    [
        [],
        []
    ],
    ["""
    
    template_end = """
    ]
];

var lastRule = '';

function FindProxyForURL(url, host) {
    for (var i = 0; i < rules.length; i++) {
        ret = testHost(host, i);
        if (ret != undefined)
            return ret;
    }
    return 'DIRECT';
}

function testHost(host, index) {
    for (var i = 0; i < rules[index].length; i++) {
        for (var j = 0; j < rules[index][i].length; j++) {
            lastRule = rules[index][i][j];
            if (host == lastRule || host.endsWith('.' + lastRule))
                return i % 2 == 0 ? 'DIRECT' : proxy;
        }
    }
    lastRule = '';
}

// REF: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/String/endsWith
if (!String.prototype.endsWith) {
    String.prototype.endsWith = function(searchString, position) {
        var subjectString = this.toString();
        if (typeof position !== 'number' || !isFinite(position) || Math.floor(position) !== position || position > subjectString.length) {
            position = subjectString.length;
        }
        position -= searchString.length;
        var lastIndex = subjectString.indexOf(searchString, position);
        return lastIndex !== -1 && lastIndex === position;
  };
}"""

    direct_str = format_js_array(direct_domains)
    proxy_str = format_js_array(proxy_domains)

    # 拼接最终的内容
    pac_content = f"{template_start}\n{direct_str},\n{proxy_str}{template_end}\n"
    
    with open('pac.txt', 'w', encoding='utf-8') as f:
        f.write(pac_content)
    print("pac.txt 生成成功，共包含 {} 个直连规则和 {} 个代理规则。".format(len(direct_domains), len(proxy_domains)))

if __name__ == '__main__':
    content = fetch_gfwlist()
    direct, proxy = parse_gfwlist(content)
    generate_pac(direct, proxy)
