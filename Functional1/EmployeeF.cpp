/*
 * EmployeeF.cpp
 *
 *  Created on: 25/05/2013
 *      Author: ben
 */

#include "EmployeeF.h"

EmployeeF::EmployeeF(const std::string& aGivenName,
			   const std::string& aFamilyName,
			   const int	aNumber,
			   const double &aSalary) :
	givenName(aGivenName),
	familyName(aFamilyName),
	number(aNumber),
	salary(aSalary)
{
}
