import os
from azure.appconfiguration import AzureAppConfigurationClient


def fetchKey(key):
    """
    Fetches the value of the specified configuration key from Azure App Configuration.

    Args:
        key (str): The configuration key to fetch.

    Returns:
        str: The value of the configuration key.

    Raises:
        Exception: If the configuration key is not found or an error occurs while fetching the value.
    """
    # connection_str = os.getenv("APP_CONFIG_CONNECTION_STRING")
    connection_str = 'Endpoint=https://perf-appconfig.azconfig.io;Id=fWd0;Secret=DwVO/onZY/Cz/ZP+SQxse/NR5Fa3wLQIXzwEGGnPVwM='
    client = AzureAppConfigurationClient.from_connection_string(connection_str)
    config_setting = client.get_configuration_setting(key=key)
    return config_setting.value
