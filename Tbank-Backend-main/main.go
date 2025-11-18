package main

import(
	// "fmt"
	"os"
	"strconv"
	loggerModule "main/loggerModule"
	databaseModule "main/databaseModule"
	tokenModule "main/tokenModule"
	mlModule "main/mlModule"
	loggerImpl "main/implementationFileLogger"
	databaseImpl "main/implementationDatabasePostgreSQL"
	tokenImpl "main/implementationTokenJWT"
	mlImpl "main/implementationMLSocket"
	api "main/api"
	"net/http"

	//userModule "main/userModule"
	//productModule "main/productModule"
	//"time"
)

func main(){
	password:=os.Getenv("PASS")
	user:=os.Getenv("USER")
	dbname:=os.Getenv("DBNAME")
	host:=os.Getenv("DBHOST")
	portstr:=os.Getenv("DBPORT")
	secretKey:=os.Getenv("APIKEY")

	port, err := strconv.ParseInt(portstr, 10, 64)
	if err!=nil{
		panic("Failed to get port from env")
	}

	loggerManagerDatabase, err := loggerImpl.NewFileLoggerManager("databaseLogs.log", "Database Module")
	if err!=nil{
		panic("Failed to create logger")
	}
	loggerManagerJWT, err := loggerImpl.NewFileLoggerManager("tokenLogs.log", "Token Module")
	if err!=nil{
		panic("Failed to create logger")
	}

	loggerManagerMainHTTP, err := loggerImpl.NewFileLoggerManager("MainHTTP.log", "HTTP API")
	if err!=nil{
		panic("Failed to create logger")
	}

	loggerServiceMainHTTP := loggerModule.NewLoggerService(loggerManagerMainHTTP)
	if err!=nil{
		panic("Failed to create logger")
	}

	databaseManager := databaseImpl.NewPostgreSQLManager(nil, host, port, user, password, dbname, loggerManagerDatabase)
	databaseManager.Open()
	databaseManager.HardReset()
	//defer databaseManager.Close()

	databaseManager.Create()

	tokenManager := tokenImpl.NewJWTTokenManager(secretKey, loggerManagerJWT)
	
	databaseService := databaseModule.NewDatabaseService(databaseManager, loggerManagerDatabase)
	tokenService := tokenModule.NewTokenService(tokenManager, loggerManagerJWT)

	mlManager := mlImpl.NewUserSocketManager("127.0.0.1", "8766", loggerManagerMainHTTP)
	mlService := mlModule.NewMLService(mlManager)

	loginHandler := api.NewLoginHandler(tokenService, databaseService, loggerServiceMainHTTP)
	messageHandler := api.NewMessageHandler(tokenService, databaseService, mlService, loggerServiceMainHTTP)



	mainHTTP := api.NewMainHandler(loginHandler, messageHandler)
	http.Handle("/", mainHTTP)
	http.ListenAndServe(":3110", mainHTTP)
}