(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_40 () (_ BitVec 70))
(assert
 (let ((?x1818 ((_ extract 69 16) i_40)))
 (let ((?x272 ((_ extract 15 0) i_40)))
 (let ((?x2886 (concat ?x272 ?x1818)))
 (let ((?x993 (bvor (bvlshr i_40 (bvurem (_ bv18446744073709551616 70) (_ bv70 70))) (bvshl i_40 (bvsub (_ bv70 70) (bvurem (_ bv18446744073709551616 70) (_ bv70 70)))))))
 (let ((?x944 (ite (and (distinct ?x993 ?x2886) true) (_ bv1 1) (_ bv0 1))))
 (not (= ?x944 (_ bv1 1)))))))))
(assert
 (let ((?x272 ((_ extract 15 0) i_40)))
(let (($x1200 (bvule ?x272 (_ bv1 16))))
(not $x1200))))
(check-sat)
