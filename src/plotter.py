from datetime import date, datetime, timedelta
from io import BytesIO
import matplotlib.pyplot as plt


class Plotter:

    @staticmethod
    async def plot_price_history(src: str, dst: str, price_history: dict[date, list[dict]]) -> BytesIO:
        plt.figure(figsize=(12, 7))
        x_dates = []

        # Create a complete sequence of dates between min and max
        all_tracking_dates = set()
        for histories in price_history.values():
            for record in histories:
                tracking_date = datetime.fromisoformat(record['dt']).date()
                all_tracking_dates.add(tracking_date)

        if all_tracking_dates:
            min_date = min(all_tracking_dates)
            max_date = max(all_tracking_dates)
            x_dates = []
            current_date = min_date
            while current_date <= max_date:
                x_dates.append(current_date)
                current_date += timedelta(days=1)

        for flight_date in sorted(price_history.keys()):
            # Create a dictionary to store the latest price for each tracking date
            daily_prices = {}

            for record in price_history[flight_date]:
                tracking_date = datetime.fromisoformat(record['dt']).date()
                # Always update with the latest price for each day
                daily_prices[tracking_date] = record['price']

            # Create y-values array, filling gaps with the last known price
            y_prices = []
            last_known_price = None
            for date in x_dates:
                if date in daily_prices:
                    last_known_price = daily_prices[date]
                    y_prices.append(last_known_price)
                elif last_known_price is not None:
                    # Fill gap with last known price
                    y_prices.append(last_known_price)
                else:
                    # If no price is known yet, use NaN to create a gap in the plot
                    y_prices.append(float('nan'))

            # Plot the line for this flight date
            plt.plot(x_dates, y_prices, marker='o', markersize=4,
                     label=f'{flight_date}', drawstyle='steps-post')

        plt.title(f'Price History for {src} → {dst}')
        plt.xlabel('Tracking Date')
        plt.ylabel('Price')
        plt.xticks(rotation=45)
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.grid(True, linestyle='--', alpha=0.6)

        # Adjust layout to prevent label cutoff
        plt.tight_layout()

        plt.ylim(bottom=0)

        # Save the plot to BytesIO buffer
        buffer = BytesIO()
        plt.savefig(buffer, format='png', bbox_inches='tight')
        buffer.seek(0)
        plt.close()

        return buffer
