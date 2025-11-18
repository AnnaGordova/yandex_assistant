package databaseModule

import (
	loggerModule "main/loggerModule"
	userModule "main/userModule"
	productModule "main/productModule"
	cartModule "main/cartModule"
	"errors"

)

var(
	ErrUserNotFound = errors.New("User was not found")
	ErrProductNotFound = errors.New("Product was not found")
)

type databaseService struct{
	databaseManager DatabaseManager
	loggerManager	loggerModule.LoggerManager
}

func NewDatabaseService(databaseManager DatabaseManager, loggerManager loggerModule.LoggerManager) DatabaseService{
	return &databaseService{
		databaseManager: databaseManager,
		loggerManager: loggerManager,
	}
}

func (dbService *databaseService) Create() error{
	return dbService.databaseManager.Create()
}

func (dbService *databaseService) Open() error{
	return dbService.databaseManager.Open()
}

func (dbService *databaseService) FindUser(login string) (*userModule.User, error){
	return dbService.databaseManager.FindUser(login)
}

func (dbService *databaseService) StoreUser(user *userModule.User) error{
	return dbService.databaseManager.StoreUser(user)
}

func (dbService *databaseService) ChangePassword(user *userModule.User) error{
	return dbService.databaseManager.ChangePassword(user)
}

func (dbService *databaseService) AddToCart(user *userModule.User, product *productModule.Product, amount int64) error{
	return dbService.databaseManager.AddToCart(user, product, amount)
}

func (dbService *databaseService) GetCart(user *userModule.User) (*cartModule.Cart, error){
	return dbService.databaseManager.GetCart(user)
}

func(dbService *databaseService) StoreProduct(product *productModule.Product) (int64, error){
	return dbService.databaseManager.StoreProduct(product)
}
func(dbService *databaseService) DeleteProduct(product *productModule.Product, user *userModule.User) error{
	return dbService.databaseManager.DeleteProduct(product, user)
}

func (dbService *databaseService) HardReset(){
	dbService.databaseManager.HardReset()
}
