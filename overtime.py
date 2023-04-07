import requests
import json
import pandas as pd
from datetime import date
import datetime as dt
from workalendar.europe import Berlin
import yaml
import click

# load yml file to dictionary
# secrets = yaml.load(open("./secrets.yml"), Loader=Any)
with open("./secrets.yml", "r") as file:
    secrets = yaml.safe_load(file)


@click.command()
@click.argument("name", required=False)
@click.option(
    "--name",
    "-n",
    type=click.Choice(list(secrets["creators"].keys()), case_sensitive=False),
    multiple=False,
    prompt="Name",
)
def overtime(name):

    # access values from dictionary
    API_KEY = secrets["timeular"]["API_KEY"]
    API_SECRET = secrets["timeular"]["API_SECRET"]

    try:
        creator = secrets["creators"][name]
    except:
        click.echo(f"{name} not found.")
        exit()

    d = dt.datetime.today() - dt.timedelta(days=2)

    year = date.today().year
    month = d.month
    day = d.day

    daterange = (
        f"{year:04}-01-01T00:00:00.000/{year:04}-{month:02}-{day:02}T23:59:59.999"
    )

    # Authenticate Timeular
    url = "https://api.timeular.com/api/v3/developer/sign-in"

    payload = '{\n  "apiKey"    : "%s",\n  "apiSecret" : "%s"\n}' % (
        API_KEY,
        API_SECRET,
    )
    headers = {"Content-Type": "application/json"}

    response = requests.request("POST", url, headers=headers, data=payload)

    body = json.loads(response.text.encode("utf8"))
    token = body["token"]

    url = f"https://api.timeular.com/api/v3/report/data/{daterange}"
    payload = {}
    headers = {"Authorization": "Bearer %s" % token}

    response = requests.request("GET", url, headers=headers, data=payload)
    body = response.json()
    timeentries = body["timeEntries"]

    df = pd.DataFrame.from_dict(timeentries)

    json_struct = json.loads(df.to_json(orient="records"))
    df = pd.json_normalize(json_struct)
    df = df[df["creator"].isin([creator])]

    df["duration.startedAt"] = pd.to_datetime(df["duration.startedAt"])
    df["duration.stoppedAt"] = pd.to_datetime(df["duration.stoppedAt"])
    df["duration"] = (
        df["duration.stoppedAt"] - df["duration.startedAt"]
    ).dt.total_seconds() / 3600

    df = df.groupby(["creator", "activity.name"])["duration"].sum().unstack()
    df.fillna(0, inplace=True)

    df.columns = df.columns.values

    df = df.T
    
    df.columns = ["hours"]
    df['%'] = df['hours']/df.sum()[0]*100
    
    click.echo(df.round(1))

    worked_hours = df.sum()[0]

    cal = Berlin()
    cal.holidays(year)

    working_hours = 8 * cal.get_working_days_delta(
        date(year, 1, 1), date(year, month, day)
    )
    overtime = worked_hours - working_hours

    click.echo(
        f"\nÜberstunden (bis einschliesslich {day:02}.{month:02}.{year:04}): {overtime.round(1):0}"
    )


if __name__ == "__main__":

    overtime()
