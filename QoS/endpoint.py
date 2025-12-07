@app.route("/qos", methods=["GET"])
def qos_ping():
    return jsonify({"status": "ok"})

@app.route("/qos")
def qos_endpoint():
    t1_server_arrival = time.time() 
    return jsonify({
        "status": "ok",
        "message": "QoS Test Response for IPLR",
        "t1_server_arrival": t1_server_arrival 
    })

