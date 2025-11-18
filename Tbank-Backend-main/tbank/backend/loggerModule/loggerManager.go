package loggerModule

type LoggerManager interface{
	INFO(string)
	WARNING(string)
	ERROR(string)
	DEBUG(string)
	Close() error
}