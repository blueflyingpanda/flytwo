def price_history_key_builder(func, namespace, request, response, *args, **kwargs) -> str:
    return f'{request.url.path}:{str(request.query_params.get("dt"))}'


def airports_key_builder(func, namespace, request, response, *args, **kwargs) -> str:
    return request.url.path
