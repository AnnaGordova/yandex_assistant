package loggerModule

type loggerService struct{
	loggerManager LoggerManager
}

func NewLoggerService(loggerManager LoggerManager) LoggerService{
	return &loggerService{
		loggerManager: loggerManager,
	}
}

func(ls *loggerService) INFO(message string){
	ls.loggerManager.INFO(message)
}

func(ls *loggerService) WARNING(message string){
	ls.loggerManager.WARNING(message)
}

func(ls *loggerService) ERROR(message string){
	ls.loggerManager.ERROR(message)
}

func(ls *loggerService) DEBUG(message string){
	ls.loggerManager.DEBUG(message)
}

func(ls *loggerService) Close() error{
	return ls.loggerManager.Close()
}