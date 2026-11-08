(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_40 () (_ BitVec 70))
(assert
 (let ((?x3121 ((_ extract 69 16) i_40)))
 (let ((?x3497 ((_ extract 15 0) i_40)))
 (let ((?x1098 (concat ?x3497 ?x3121)))
 (let ((?x92 (bvor (bvlshr i_40 (bvurem (_ bv18446744073709551616 70) (_ bv70 70))) (bvshl i_40 (bvsub (_ bv70 70) (bvurem (_ bv18446744073709551616 70) (_ bv70 70)))))))
 (let ((?x2625 (ite (and (distinct ?x92 ?x1098) true) (_ bv1 1) (_ bv0 1))))
 (not (= ?x2625 (_ bv1 1)))))))))
(assert
 (let ((?x3497 ((_ extract 15 0) i_40)))
(let (($x601 (bvule ?x3497 (_ bv1 16))))
(not $x601))))
(check-sat)
