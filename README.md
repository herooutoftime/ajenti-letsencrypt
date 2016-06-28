# Ajenti LetsEncrypt Plugin

**BETA VERSION: USE WITH CAUTION**

Easily create Let's Encrypt signed certificates to secure your server

## Installation

```
# Clone this repository to <ajenti_source>/plugins
git@github.com:herooutoftime/ajenti-letsencrypt.git

# Restart Ajenti
service ajenti restart (debian)
# Run in debug mode
ajenti-panel -v
```

## Usage

* In Ajenti-Panel go to `Security -> LetsEncrypt`
* Replace your config options depending on your os
* Fill in the domains you want to create certificates for
  * 1 domain per row (e.g.: domain.com sub.domain.com another.domain.com)
* Click `Apply` and your certificates are being generated and stored to your chosen destination (`basedir`)
* Set the SSL-certificates per domain in your `Websites` tabs

## Support

Please [open an issue](https://github.com/herooutoftime/ajenti-letsencrypt/issues/new) for support.
