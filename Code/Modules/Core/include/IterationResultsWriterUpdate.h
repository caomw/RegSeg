/*
 * IterationResultsWriterUpdate.h
 *
 *  Created on: Oct 16, 2013
 *      Author: oesteban
 */

#ifndef ITERATIONRESULTSWRITERUPDATE_H_
#define ITERATIONRESULTSWRITERUPDATE_H_

#include "IterationUpdate.h"

#include <itkImageFileWriter.h>
#include "DisplacementFieldFileWriter.h"
#include "DisplacementFieldComponentsFileWriter.h"

namespace rstk {

template< typename TOptimizer >
class IterationResultWriterUpdate: public IterationUpdate<TOptimizer>
{
public:
	typedef IterationResultWriterUpdate                 Self;
	typedef TOptimizer                                  OptimizerType;
	typedef typename itk::WeakPointer<OptimizerType>    OptimizerPointer;
	typedef IterationUpdate<TOptimizer>                 Superclass;
	typedef itk::SmartPointer<Self>                     Pointer;
	typedef itk::SmartPointer< const Self >             ConstPointer;

	typedef typename OptimizerType::FieldType                   FieldType;
	typedef typename OptimizerType::CoefficientsImageType       CoefficientsImageType;
	typedef typename OptimizerType::CoefficientsImageArray      CoefficientsImageArray;
	typedef typename OptimizerType::FunctionalType      		FunctionalType;
	typedef typename FunctionalType::ROIType                    ROIType;
	typedef typename FunctionalType::ProbabilityMapType 		ProbabilityMapType;
	typedef typename FunctionalType::ShapeGradientType          ShapeGradientType;
	typedef itk::QuadEdgeMeshScalarDataVTKPolyDataWriter
			                             < ShapeGradientType >  ContourWriterType;
	typedef typename ContourWriterType::Pointer                 ContourWriterPointer;


	typedef rstk::DisplacementFieldComponentsFileWriter<FieldType> ComponentsWriter;
	typedef itk::ImageFileWriter< ProbabilityMapType >  MapWriter;
	typedef typename itk::ImageFileWriter< CoefficientsImageType > CoefficientsWriter;

	itkTypeMacro( IterationResultWriterUpdate, IterationUpdate ); // Run-time type information (and related methods)
	itkNewMacro( Self );

    void Execute(const itk::Object * object, const itk::EventObject & event) {
    	std::string prefix = "";

    	if ( this->m_Prefix.size() > 0 ) {
    		prefix = this->m_Prefix + "_";
    	}

    	if( typeid( event ) == typeid( itk::IterationEvent ) ) {
    		std::stringstream ss;

    		CoefficientsImageArray coeff = this->m_Optimizer->GetCoefficients();
    		CoefficientsImageArray speed = this->m_Optimizer->GetDerivativeCoefficients();

    		for ( size_t i = 0; i< coeff.Size(); i++) {
				typename CoefficientsWriter::Pointer p = CoefficientsWriter::New();
				ss.str("");
				ss << prefix << "coeff_speed_" << std::setfill('0')  << "lev" << this->m_Level << "_it" << std::setw(3) << this->m_Optimizer->GetCurrentIteration() << "_cmp" << std::setw(1) << i << ".nii.gz";
				p->SetFileName( ss.str().c_str() );
				p->SetInput( speed[i] );
				p->Update();

				ss.str("");
				ss << prefix << "coeff_value_" << std::setfill('0') << "lev" << this->m_Level << "_it"  << std::setw(3) << this->m_Optimizer->GetCurrentIteration() << "_cmp" << std::setw(1) << i << ".nii.gz";
				p->SetFileName( ss.str().c_str() );
				p->SetInput( coeff[i] );
				p->Update();
    		}

     		typename ComponentsWriter::Pointer f = ComponentsWriter::New();
    		ss.str("");
    		ss << prefix << "field_" << std::setfill('0') << "lev" << this->m_Level << "_it"  << std::setw(3) << this->m_Optimizer->GetCurrentIteration();
    		f->SetFileName( ss.str().c_str() );
    		f->SetInput( this->m_Optimizer->GetCurrentDisplacementField() );
    		f->Update();

       		size_t nContours =this->m_Optimizer->GetFunctional()->GetCurrentContours().size();

       		for( size_t r = 0; r <= nContours; r++){
        		ss.str("");
        		ss << prefix << "region_" << r  << "lev" << this->m_Level << "_it" << std::setfill('0')<<std::setw(3) << this->m_Optimizer->GetCurrentIteration() << ".nii.gz";
        		typename MapWriter::Pointer wr = MapWriter::New();
        		wr->SetInput( this->m_Optimizer->GetFunctional()->GetCurrentMap(r));
        		wr->SetFileName(ss.str().c_str() );
        		wr->Update();
        	}

       		typename FunctionalType::ShapeGradientList grads = this->m_Optimizer->GetFunctional()->GetGradients();
       		for( size_t r = 0; r < nContours; r++ ) {
       			ContourWriterPointer wc = ContourWriterType::New();
       			std::stringstream ss;
       			ss << "gradients_lev" << this->m_Level << "_it" << std::setfill('0')<<std::setw(3) << this->m_Optimizer->GetCurrentIteration() << std::setw(2) << "_cont"<< r << ".vtk";
       			wc->SetFileName( ss.str().c_str() );
       			wc->SetInput( grads[r] );
       			wc->Update();
       		}
    	}

    	if (typeid( event ) == typeid( itk::StartEvent )) {
			typedef itk::ImageFileWriter< ROIType > WriteROI;
			typename WriteROI::Pointer w = WriteROI::New();
			std::stringstream ss;
			ss << prefix << "regions_" << this->m_Level << ".nii.gz";
			w->SetFileName( ss.str().c_str() );
			w->SetInput( this->m_Optimizer->GetFunctional()->GetCurrentRegions() );
			w->Update();

    	}
    }

    itkSetMacro( Prefix, std::string );
    itkGetConstMacro( Prefix, std::string );

    void SetOptimizer( OptimizerType * optimizer ) {
      m_Optimizer = optimizer;
      m_Optimizer->AddObserver( itk::IterationEvent(), this );
      m_Optimizer->AddObserver( itk::StartEvent(), this );
      m_Optimizer->AddObserver( itk::EndEvent(), this );
    }

protected:
    IterationResultWriterUpdate(){}
    ~IterationResultWriterUpdate(){}

private:
    IterationResultWriterUpdate( const Self & ); // purposely not implemented
	void operator=( const Self & ); // purposely not implemented

	OptimizerPointer   m_Optimizer;
	std::string        m_Prefix;
};

} // end namespace rstk

#endif /* ITERATIONRESULTSWRITERUPDATE_H_ */
