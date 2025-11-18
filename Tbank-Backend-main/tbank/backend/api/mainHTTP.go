package api

import(
	"net/http"
	"encoding/json"
)

type MainHandler interface{
	ServeHTTP(writer http.ResponseWriter, request *http.Request)
}

type mainHandler struct{
	loginHandler LoginHandler
	messageHandler MessageHandler
}

func NewMainHandler(loginHandler LoginHandler, messageHandler MessageHandler) MainHandler{
	return &mainHandler{
		loginHandler: loginHandler,
		messageHandler: messageHandler,
	}
}

func (mh *mainHandler) ServeHTTP(writer http.ResponseWriter, request *http.Request){
	// Set CORS headers
    writer.Header().Set("Access-Control-Allow-Origin", "*")
    writer.Header().Set("Access-Control-Allow-Methods", "POST, OPTIONS")
    writer.Header().Set("Access-Control-Allow-Headers", "Content-Type, Action")
    writer.Header().Set("Content-Type", "application/json")

	if request.Method == "OPTIONS" {
        return
    }

	if request.Method != http.MethodPost {
        sendError(writer, "Not Allowed HTTP Method", http.StatusBadRequest)
        return
    }

	action := request.Header.Get("action")
    if action == "" {
        sendError(writer, "Action header is required", http.StatusBadRequest)
        return
    }

	switch action{
	case "handleLogin": 
		response, _ := mh.loginHandler.Login(writer, request)
		json.NewEncoder(writer).Encode(response)
	case "handleRegister":
		response, _ := mh.loginHandler.Register(writer, request)
		json.NewEncoder(writer).Encode(response)
	case "changePassword":
		response, _ := mh.loginHandler.ChangePassword(writer, request)
		json.NewEncoder(writer).Encode(response)
	case "likeProduct":
		response, _ := mh.messageHandler.SaveProduct(writer, request)
		json.NewEncoder(writer).Encode(response)
	case "messageML":
		response, _ := mh.messageHandler.IterMessage(writer, request)
		json.NewEncoder(writer).Encode(response)
	case "getCart":
		response, _ := mh.messageHandler.GetCart(writer, request)
		json.NewEncoder(writer).Encode(response)
	case "deleteProduct":
		response, _ := mh.messageHandler.DeleteProduct(writer, request)
		json.NewEncoder(writer).Encode(response)
	}

	return
}

func sendError(w http.ResponseWriter, message string, statusCode int) {
    w.WriteHeader(statusCode)
    json.NewEncoder(w).Encode(MessageResponse{
        Success: false,
        Message: message,
    })
}