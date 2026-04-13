from datetime import date, datetime, timedelta
from io import BytesIO

import matplotlib.pyplot as plt
import numpy as np
from pydantic import BaseModel, RootModel


class MissingPriceHistory(Exception):
    """Raised when no price history is available"""


class PricePoint(BaseModel):
    price: int
    dt: datetime


class PriceHistory(RootModel):
    root: dict[date, list[PricePoint]]


class Plotter:
    @staticmethod
    async def plot_price_history(src: str, dst: str, price_history: dict[date, list[PricePoint]]) -> BytesIO:
        fig, ax = plt.subplots(figsize=(10, 6))

        offset = 0.3  # otherwise graph lines might overlap

        # Seaborn Tab10 colors. Avoiding seaborn for minimal dependencies
        colors = [
            '#1F77B4',
            '#FF7F0E',
            '#2CA02C',
            '#D62728',
            '#9467BD',
            '#8C564B',
            '#E377C2',
            '#7F7F7F',
            '#BCBD22',
            '#17BECF',
        ]

        all_tracking_dates = set()

        # Collect all tracking dates to establish a common X-axis
        for histories in price_history.values():
            for record in histories:
                tracking_date = record.dt.date()
                all_tracking_dates.add(tracking_date)

        if not all_tracking_dates:
            raise MissingPriceHistory('No price history available')

        min_date, max_date = min(all_tracking_dates), max(all_tracking_dates)
        x_dates = [min_date + timedelta(days=i) for i in range((max_date - min_date).days + 1)]
        x_ticks = np.array([(d - min_date).days for d in x_dates])  # Convert dates to numerical format

        for i, (flight_date, records) in enumerate(sorted(price_history.items())):
            daily_prices = {}

            for record in records:
                tracking_date = record.dt.date()
                daily_prices[tracking_date] = record.price

            y_prices = []
            last_known_price = None
            for dt in x_dates:
                if dt in daily_prices:
                    last_known_price = daily_prices[dt]
                    y_prices.append(last_known_price + (i * offset))  # Small offset to prevent overlap
                elif last_known_price is not None:
                    y_prices.append(last_known_price + (i * offset))  # Maintain offset for gaps
                else:
                    y_prices.append(None)

            # Convert data for plotting (filter out None values)
            valid_indices = [j for j, y in enumerate(y_prices) if y is not None]
            x_valid = np.array([x_ticks[j] for j in valid_indices])
            y_valid = np.array([y_prices[j] for j in valid_indices])

            if len(x_valid) > 1:  # Ensure enough points for plotting
                ax.plot(x_valid, y_valid, color=colors[i % len(colors)], linewidth=2, label=f'{flight_date}')

            # Add markers at actual data points
            ax.scatter(x_valid, y_valid, color=colors[i % len(colors)], s=50, marker='o', edgecolors='black')

        ax.set_title(f'Price History for {src} → {dst}')
        ax.set_xlabel('Tracking Date')
        ax.set_ylabel('Price')
        ax.legend(title='Flight Dates')
        ax.grid(True, linestyle='--', alpha=0.5)
        ax.set_xticks(x_ticks[:: max(1, len(x_ticks) // 10)])  # Limit tick labels for readability
        ax.set_xticklabels([d.strftime('%Y-%m-%d') for d in x_dates[:: max(1, len(x_ticks) // 10)]], rotation=45)

        # Save plot to PNG buffer
        png_buffer = BytesIO()
        plt.savefig(png_buffer, format='png', bbox_inches='tight', dpi=100)
        plt.close(fig)
        png_buffer.seek(0)

        return png_buffer  # Return PNG buffer
