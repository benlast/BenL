//A non-functional Employee class

#include <string>

class EmployeeNF {
public:
	//The constructor body is in EmployeeNF.cpp so that
	//there's something for the linker to use.
	EmployeeNF(const std::string& aGivenName,
			   const std::string& aFamilyName,
			   const int	aNumber,
			   const double &aSalary);

	void SetNumber(const int aNumber) {
		number=aNumber;
	}

	int Number() const {
		return number;
	}

	void SetSalary(const double& aSalary) {
		salary=aSalary;
	}

	double Salary() const {
		return salary;
	}

	void SetGivenName(const std::string& aGivenName) {
		givenName=aGivenName;
	}

	std::string GivenName() const {
		return givenName;
	}

	void SetFamilyName(const std::string& aFamilyName) {
		familyName=aFamilyName;
	}

	std::string FamilyName() const {
		return familyName;
	}

private:
	std::string	givenName;
	std::string	familyName;
	int			number;
	double		salary;
};
