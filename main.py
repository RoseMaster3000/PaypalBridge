from PaypalWebsite import app

if __name__ == '__main__':
    # ---------------------------------------------
    # INTERNAL ACCESS ONLY (PC <--> PC)
    # 127.0.0.1:5000
    # Use this when you want:
    # - yellow debug page
    # - auto-reload
    # - browser debugging on your PC
    # NOT suitable for phone access.
    # ---------------------------------------------
     app.run(host='0.0.0.0', port=5000, debug=True)

    # ---------------------------------------------
    # EXTERNAL + INTERNAL ACCESS (PC <--> Phone AND PC <--> PC)
    # 192.168.x.x:5000 - external (LAN IP from locanhost PC)
    # 127.0.0.1:5000 - internal
    # Use this for Unity Editor + Android testing.
    # - stable mode
    # - supports multiple requests (threaded=True)
    # - works on LAN (phone can connect)
    # - no yellow debug page
    # ---------------------------------------------
    # app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)