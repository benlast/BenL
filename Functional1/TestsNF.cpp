/*
 * TestsNF.cpp
 *
 *  Created on: 25/05/2013
 *      Author: ben
 *  Tests for the non-functional Employee class
 */

#include "EmployeeNF.h"
#include <gtest/gtest.h>

TEST(EmployeeNF,BasicTests) {
	// Create a simple employee instance
	EmployeeNF e("Ben","Last",1,1000.0);

	//Verify values
	ASSERT_EQ(e.GivenName(),"Ben");
	ASSERT_EQ(e.FamilyName(),"Last");
	ASSERT_EQ(e.Number(),1);
	ASSERT_EQ(e.Salary(),1000.0);

	//Change values and verify the changes
	e.SetGivenName("Attila");
	ASSERT_EQ(e.GivenName(),"Attila");
	e.SetFamilyName("Gonzalez");
	ASSERT_EQ(e.FamilyName(),"Gonzalez");
	e.SetNumber(123);
	ASSERT_EQ(e.Number(),123);
	e.SetSalary(2048.1024);
	ASSERT_EQ(e.Salary(),2048.1024);
}
