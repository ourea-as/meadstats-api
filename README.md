# Meadstats API

API between Meadstats Frontend and Untappd API.
Stores and aggregates statistics.

## Getting Started

Docker is the recommended option for deployment, but if you need a local option you cna follow these steps.

### Prerequisites

* A PostgreSQL Server
* Python 3
* Untappd API Key

### Installing

* Install python dependencies
  * `pip install -r requirements.txt`
* Set up a database
* Set environment variables
* Initialize database
  * `python manage.py upgrade`
* Start with command
  * `flask run`

### Environment Variables

| Variable      | Description                                | Default Value                |
| ------------- | ------------------------------------------ | ---------------------------- |
| FLASK_ENV     | Set to either production or development    | development                  |
| APP_SETTINGS  | Production or development (To be removed)  | app.config.DevelopmentConfig |
| DATABASE_URL  | Set to a PostgreSQL connection string      | < Not set >                  |
| JWT_SECRET    | Used to generate JWT tokens                | < Not set >                  |
| CLIENT_SECRET | Untappd API Client Secret                  | < Not set >                  |
| CLIENT_ID     | Untappd API Client ID                      | < Not set >                  |

## Deployment

Prebuilt docker images can be found on dockerhub.
Deployment using docker requires the same environment variables to be set.

## Contributing

Please send me a pull request or issue if there is a feature you want or some issue you find.

## License

This project is licensed under the GPL-3.0 License - see the [LICENSE](LICENSE) file for details