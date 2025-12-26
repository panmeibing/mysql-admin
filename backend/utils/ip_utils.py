from fastapi import Request


class IpUtil:
    @staticmethod
    def get_real_client_ip(request: Request) -> str:
        x_forwarded_for = request.headers.get('X-Forwarded-For')
        if x_forwarded_for:
            # X-Forwarded-For 可能有多个IP, 取第一个
            ip = x_forwarded_for.split(',')[0].strip()
            return ip
        x_real_ip = request.headers.get('X-Real-Ip')
        if x_real_ip:
            return x_real_ip
        return request.client.host
