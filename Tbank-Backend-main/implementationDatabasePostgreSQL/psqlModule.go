package implementationDatabasePostgreSQL

import (
	"fmt"
	"database/sql"
	"io/ioutil"
	"strings"
	loggerModule "main/loggerModule"
	databaseModule "main/databaseModule"
	userModule	 "main/userModule"
	cartModule   "main/cartModule"
	productModule "main/productModule"
	_ "github.com/lib/pq"
)

var(
	createCart string = "implementationDatabasePostgreSQL/sqlCode/DDL/createCart.sql"
	createCartItem string = "implementationDatabasePostgreSQL/sqlCode/DDL/createCartItem.sql"
	createUser string = "implementationDatabasePostgreSQL/sqlCode/DDL/createUser.sql"
	createProduct string = "implementationDatabasePostgreSQL/sqlCode/DDL/createProduct.sql"

	findUser string = "implementationDatabasePostgreSQL/sqlCode/DML/findUser.sql"
	storeUser string = "implementationDatabasePostgreSQL/sqlCode/DML/storeUser.sql"
	changePassword string = "implementationDatabasePostgreSQL/sqlCode/DML/changePassword.sql"
	storeProduct string = "implementationDatabasePostgreSQL/sqlCode/DML/storeProduct.sql"
	storeCart string = "implementationDatabasePostgreSQL/sqlCode/DML/storeCart.sql"
	getCart string = "implementationDatabasePostgreSQL/sqlCode/DML/getCart.sql"
	deleteProduct string = "implementationDatabasePostgreSQL/sqlCode/DML/deleteProduct.sql"

	hardDrop string = "implementationDatabasePostgreSQL/sqlCode/DDL/hardDrop.sql"
)

type postgreSQLManager struct{
	DBase *sql.DB
	Host string
	Port int64
	User string
	Password string
	DBName string
	logger loggerModule.LoggerManager
}

func NewPostgreSQLManager(DBase *sql.DB, Host string, Port int64, User string, Password string, DBName string, logger loggerModule.LoggerManager) databaseModule.DatabaseManager{
	return &postgreSQLManager{
		DBase: DBase,
		Host: Host,
		Port: Port,
		User: User,
		Password: Password,
		DBName: DBName,
		logger: logger,
	}
}

func (psqlManager *postgreSQLManager) readScript(filepath string) (string, error) {
	sqlBytes, err := ioutil.ReadFile(filepath)

	if err!=nil{
		psqlManager.logger.ERROR(fmt.Sprintf("Failed opening SQL Script: %s", filepath))
		return "", err
	}

	sqlScript := string(sqlBytes)

	return sqlScript, nil
}

func (psqlManager *postgreSQLManager) execSQLScript(filepath string) error{
	sqlScript, err := psqlManager.readScript(filepath)

	if err != nil{
		return err
	}

	_, err = psqlManager.DBase.Exec(sqlScript)

	if err!=nil{
		psqlManager.logger.ERROR(fmt.Sprintf("Failed to Execute SQL Script: %s", filepath))
		return err
	}

	return nil
}

func (psqlManager *postgreSQLManager) Open() error{
	connStr := fmt.Sprintf("host=%s port=%d user=%s password=%s dbname=%s sslmode=disable",
        psqlManager.Host, psqlManager.Port, psqlManager.User, psqlManager.Password, psqlManager.DBName)
	

	psqlManager.logger.DEBUG(connStr)
	db, err := sql.Open("postgres", connStr)

    if err != nil {
        psqlManager.logger.ERROR(fmt.Sprintf("failed to open database: %s", err))
		return err
    }

	if err := db.Ping(); err != nil {
        psqlManager.logger.ERROR(fmt.Sprintf("failed to ping database: %s", err))
		return err
    }

	psqlManager.DBase = db

	psqlManager.logger.INFO("Success in open and ping database")

	return err
}

func (psqlManager *postgreSQLManager) CreateDDLUser() error{
	err := psqlManager.execSQLScript(createUser)
	if err!=nil{
		psqlManager.logger.ERROR("Failed to create Table User when executing DDL Script")
		return err
	}

	psqlManager.logger.INFO("Success in create User DDL")
	return nil
}

func (psqlManager *postgreSQLManager) CreateDDLProduct() error{
	err := psqlManager.execSQLScript(createProduct)
	if err!=nil{
		psqlManager.logger.ERROR("Failed to create Table Product when executing DDL Script")
		return err
	}

	psqlManager.logger.INFO("Success in create Product DDL")
	return nil
}

func (psqlManager *postgreSQLManager) CreateDDLCartItem() error{
	err := psqlManager.execSQLScript(createCartItem)
	if err!=nil{
		psqlManager.logger.ERROR("Failed to create Table CartItem when executing DDL Script")
		return err
	}

	psqlManager.logger.INFO("Success in create Cart Item DDL")
	return nil
}

func (psqlManager *postgreSQLManager) Create() error{
	err := psqlManager.CreateDDLUser()
	if err!=nil{
		return err
	}

	err = psqlManager.CreateDDLProduct()
	if err!=nil{
		return err
	}

	err = psqlManager.CreateDDLCartItem()
	if err!=nil{
		return err
	}

	psqlManager.logger.INFO("Success in full DDL Creation")
	return nil
}

func (psqlManager *postgreSQLManager) FindUser(email string)(*userModule.User, error){
	sqlScript, err := psqlManager.readScript(findUser)

	if err!=nil{
		psqlManager.logger.ERROR("Error when searching user. Failed to read SQL script")
		return nil, err
	}

	finalQuery := strings.ReplaceAll(sqlScript, "{{email}}", fmt.Sprintf("'%s'", email))
	
	rows, err := psqlManager.DBase.Query(finalQuery)
    if err != nil {
		psqlManager.logger.WARNING("Error when searching user")
        return nil, err
    }

    defer rows.Close()

	for rows.Next(){
		var db_id string
		var db_email string
		var db_password string

		err = rows.Scan(&db_id, &db_email, &db_password)
		if err!=nil{
			psqlManager.logger.WARNING("Failed to parse database answer")
		}

		if db_email == email{
			psqlManager.logger.INFO("User found sucessfully")
			return &userModule.User{ID: db_id, Email: db_email, Password: db_password}, nil
		}
	}

	psqlManager.logger.WARNING("User was not found")
	
	return nil, databaseModule.ErrUserNotFound
}

func (psqlManager *postgreSQLManager) StoreUser(user *userModule.User) error{
	sqlScript, err := psqlManager.readScript(storeUser)

	if err!=nil{
		psqlManager.logger.ERROR("Error when saving user. Failed to read SQL script")
		return err
	}

	finalQuery := strings.ReplaceAll(sqlScript, "{{user_email}}", fmt.Sprintf("'%s'", user.Email))
	finalQuery = strings.ReplaceAll(finalQuery, "{{user_password}}", fmt.Sprintf("'%s'", user.Password))

	_, err = psqlManager.DBase.Exec(finalQuery)

	if err!=nil{
		psqlManager.logger.ERROR("Error when saving user in database")
	}

	psqlManager.logger.INFO("User saved in database sucessfully")
	return nil
}

func (psqlManager *postgreSQLManager) ChangePassword(user *userModule.User) error{
	sqlScript, err := psqlManager.readScript(changePassword)

	if err!=nil{
		psqlManager.logger.ERROR("Error when changning password. Failed to read SQL script")
		return err
	}

	finalQuery := strings.ReplaceAll(sqlScript, "{{user_email}}", fmt.Sprintf("'%s'", user.Email))
	finalQuery = strings.ReplaceAll(finalQuery, "{{user_password}}", fmt.Sprintf("'%s'", user.Password))


	_, err = psqlManager.DBase.Exec(finalQuery)

	if err!=nil{
		psqlManager.logger.ERROR("Error when updating password in database")
	}

	psqlManager.logger.INFO("Password changed sucessfully")
	return nil
}

func(psqlManager *postgreSQLManager) StoreProduct(product *productModule.Product) (int64, error){
	sqlScript, err := psqlManager.readScript(storeProduct)
	if err!=nil{
		psqlManager.logger.ERROR("Error when saving product. Failed to read SQL script")
		return -1, err
	}

	finalQuery := strings.ReplaceAll(sqlScript, "{{product_name}}", fmt.Sprintf("'%s'", product.Name))
	finalQuery = strings.ReplaceAll(finalQuery, "{{product_link}}", fmt.Sprintf("'%s'", product.Link))
	finalQuery = strings.ReplaceAll(finalQuery, "{{product_description}}", fmt.Sprintf("'%s'", product.Description))
	finalQuery = strings.ReplaceAll(finalQuery, "{{product_price}}", fmt.Sprintf("%f", product.Price))
	finalQuery = strings.ReplaceAll(finalQuery, "{{product_picture}}", fmt.Sprintf("'%s'", product.Picture))
	finalQuery = strings.ReplaceAll(finalQuery, "{{product_rating}}", fmt.Sprintf("%f", product.Rating))
	finalQuery = strings.ReplaceAll(finalQuery, "{{product_views}}", fmt.Sprintf("%d", product.AmmountOfReviews))
	finalQuery = strings.ReplaceAll(finalQuery, "{{product_size}}", fmt.Sprintf("'%s'", product.Size))

	rows, err := psqlManager.DBase.Query(finalQuery)

    if err != nil {
		psqlManager.logger.ERROR("Error when saving product")
        return -1, err
    }

    defer rows.Close()
	var db_id int64

	if rows.Next(){
		err = rows.Scan(&db_id)
		if err!=nil{
			psqlManager.logger.WARNING("Failed to parse database answer")
		}

		psqlManager.logger.INFO("Product added sucessfully")
		product.ID = db_id
		return db_id, nil
	}

	psqlManager.logger.WARNING("Something went wrong when saving product")
	return -1, databaseModule.ErrProductNotFound
}


func (psqlManager *postgreSQLManager) AddToCart(user *userModule.User, product *productModule.Product, amount int64) error{
	sqlScript, err := psqlManager.readScript(storeCart)
	if err!=nil{
		psqlManager.logger.ERROR("Error when adding to cart. Failed to read SQL script")
		return err
	}

	finalQuery := strings.ReplaceAll(sqlScript, "{{user_id}}", fmt.Sprintf("%s", user.ID))
	finalQuery = strings.ReplaceAll(finalQuery, "{{product_id}}", fmt.Sprintf("%d", product.ID))
	finalQuery = strings.ReplaceAll(finalQuery, "{{quantity}}", fmt.Sprintf("%d", amount))
	
	_, err = psqlManager.DBase.Exec(finalQuery)

	if err!=nil{
		psqlManager.logger.ERROR("Error when adding product to cart")
		return err
	}
	
	psqlManager.logger.INFO("Success addition to cart")
	return nil
}

func (psqlManager *postgreSQLManager) GetCart(user *userModule.User) (*cartModule.Cart, error){
	sqlScript, err := psqlManager.readScript(getCart)
	if err!=nil{
		psqlManager.logger.ERROR("Error when getting the cart. Failed to read SQL script")
		return nil, err
	}

	finalQuery := strings.ReplaceAll(sqlScript, "{{user_id}}", fmt.Sprintf("%s", user.ID))
	rows, err := psqlManager.DBase.Query(finalQuery)

    if err != nil {
		psqlManager.logger.ERROR("Error when getting the cart")
        return nil, err
    }

	defer rows.Close()

	var cart [] *productModule.Product

	for rows.Next(){
		product := productModule.Product{}
		err = rows.Scan(&product.ID, &product.Name, &product.Link, &product.Description, &product.Price, &product.Picture, &product.Rating, &product.AmmountOfReviews, &product.Size, &product.CountOfProduct)
		if err!=nil{
			psqlManager.logger.WARNING("Failed to parse database answer")
		}

		cart = append(cart, &product)
	}

	cartAns := &cartModule.Cart{CartProducts: cart}

	psqlManager.logger.INFO("Cart is ready")
	return cartAns, nil
}

func (psqlManager *postgreSQLManager) HardReset(){
	err := psqlManager.execSQLScript(hardDrop)
	if err!=nil{
		psqlManager.logger.ERROR("Failed to make Hard Drop for all tables")
	}

	psqlManager.logger.INFO("Success in Hard Drop")
}

func (psqlManager *postgreSQLManager) DeleteProduct(product *productModule.Product, user *userModule.User) error{
	sqlScript, err := psqlManager.readScript(deleteProduct)
	if err!=nil{
		psqlManager.logger.ERROR("Error when deleting the product. Failed to read SQL script")
		return err
	}

	finalQuery := strings.ReplaceAll(sqlScript, "{{user_id}}", fmt.Sprintf("%s", user.ID))
	finalQuery = strings.ReplaceAll(finalQuery, "{{product_id}}", fmt.Sprintf("%s", user.ID))
	_, err = psqlManager.DBase.Exec(finalQuery)

	if err!=nil{
		psqlManager.logger.ERROR("Error when deleting product")
		return err
	}
	
	psqlManager.logger.INFO("Success in deleting product")
	return nil
}




