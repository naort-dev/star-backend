# Starsona

Mobile application targeted for social and entertainment use. The app enables
users to request personalized videos with customized messages/wishes from 
celebrities, which can then be sent as gifts to their friends.


## Built With

* [Django](https://www.djangoproject.com/) - The framework used

## Installing

Starsona is configured with a single command deployment which will
be downloading all the latest changes from the GIT server. Downloads all
the required packages which are necessary for running the Starsona application.

Prepares or modify the Database and load the fixture datas from the files
based on the build environment (Development or Live).
Restarts the gunicorn server.

### For Development Environment

```
make setup
```

### For Live Environment

```
make setup env=live
```


## Versioning

We use [Github](https://github.com/Starsona/Starsona-backend) for versioning.


<!--## Authors-->

<!--* **Akhilraj N S** [Github](https://github.com/akhilrajns)-->
<!--* **Kanish M**-->
