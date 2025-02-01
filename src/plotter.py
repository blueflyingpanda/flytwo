from datetime import datetime, timedelta
from io import BytesIO
import plotly.graph_objects as go
import cairosvg

class Plotter:
    @staticmethod
    async def plot_price_history(src: str, dst: str, price_history: dict) -> BytesIO:
        fig = go.Figure()
        x_dates = []

        # Define distinct colors for different flight paths
        colors = ['#E63946', '#F4A261', '#2A9D8F', '#264653', '#8AB17D', '#9A348E', '#E76F51']

        all_tracking_dates = set()
        for histories in price_history.values():
            for record in histories:
                tracking_date = datetime.fromisoformat(record['dt']).date()
                all_tracking_dates.add(tracking_date)

        if all_tracking_dates:
            min_date, max_date = min(all_tracking_dates), max(all_tracking_dates)
            x_dates = [min_date + timedelta(days=i) for i in range((max_date - min_date).days + 1)]

        for i, (flight_date, records) in enumerate(sorted(price_history.items())):
            daily_prices = {}

            for record in records:
                tracking_date = datetime.fromisoformat(record['dt']).date()
                daily_prices[tracking_date] = record['price']

            y_prices = []
            last_known_price = None
            for date in x_dates:
                if date in daily_prices:
                    last_known_price = daily_prices[date]
                    y_prices.append(last_known_price)
                elif last_known_price is not None:
                    y_prices.append(last_known_price)  # Fill gap with last known price
                else:
                    y_prices.append(None)

            fig.add_trace(go.Scatter(
                x=x_dates,
                y=y_prices,
                mode='lines+markers',
                name=f'{flight_date}',
                line=dict(color=colors[i % len(colors)], width=3, shape='spline'),
                marker=dict(size=8, symbol='circle')
            ))

        fig.update_layout(
            title=f'Price History for {src} -> {dst}',
            xaxis_title='Tracking Date',
            yaxis_title='Price',
            legend_title='Flight Dates',
            xaxis=dict(showgrid=True, gridcolor='lightgrey', gridwidth=0.5),
            yaxis=dict(showgrid=True, gridcolor='lightgrey', gridwidth=0.5),
            plot_bgcolor='white'
        )

        # No kaleido needed - gives code 137 out of memory upon yc installation
        svg_data = fig.to_image(format='svg')

        png_buffer = BytesIO()
        cairosvg.svg2png(bytestring=svg_data, write_to=png_buffer)
        png_buffer.seek(0)

        return png_buffer
