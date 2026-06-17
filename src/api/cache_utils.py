def price_history_key_builder(func, namespace, request, response, *args, **kwargs) -> str:
    dt = request.query_params.get('dt')
    currency = request.query_params.get('currency')
    return f'{request.url.path}:{dt}:{currency}'


def airports_key_builder(func, namespace, request, response, *args, **kwargs) -> str:
    return request.url.path
