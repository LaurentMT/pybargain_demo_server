# Python demo server for the Bargaining Protocol

This is the implementation of a server hosting an automated seller. The bot is really stupid (random bargaining and very limited vocabulary) but it provides a support to test the protocol with the client part of the demo.

Online demo : http://vps90685.ovh.net:8083/


## Python versions

Python 2.7.6


## Dependencies

Flask (http://flask.pocoo.org/) - A microframework for web development
```
pip install flask
```

PyBitcoinTools (https://github.com/vbuterin/pybitcointools) - A python library for Bitcoin
```
python setup.py install
```

pybargain_protocol (https://github.com/LaurentMT/pybitid) - A python library for the Bargaining protocol
```
Gets the library from Github : https://github.com/LaurentMT/pybargain_protocol/archive/master.zip
Unzips the archive in a temp directory
python setup.py install
```


## Usage

The server listen by default on http://localhost:8082/bargain with flask run in debug mode
The negotiation is done on the test network
These behaviours can be changed by modyfing pybargain_demo_server\seller_demo.py


## Links
 - Bargaining protocol : https://github.com/LaurentMT/bargaining_protocol
 - Python Bargaining Protocol library : https://github.com/LaurentMT/pybargain_protocol
 - Demo client : https://github.com/LaurentMT/pybargain_demo_client


## Author
Twitter: @LaurentMT


## Contributing

1. Fork it
2. Create your feature branch (`git checkout -b my-new-feature`)
3. Commit your changes (`git commit -am 'Add some feature'`)
4. Push to the branch (`git push origin my-new-feature`)
5. Create new Pull Request
