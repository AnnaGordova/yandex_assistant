package databaseModule

import userModule "main/userModule"
import cartModule "main/cartModule"
import productModule "main/productModule"

type DatabaseManager interface{
	Open() error
	Create() error

	FindUser(string)(*userModule.User, error)
	StoreUser(*userModule.User) error
	ChangePassword(*userModule.User) error
	AddToCart(*userModule.User, *productModule.Product, int64) error
	GetCart(*userModule.User) (*cartModule.Cart, error)
	StoreProduct(*productModule.Product) (int64, error)
	DeleteProduct(*productModule.Product, *userModule.User) error
	HardReset()
}