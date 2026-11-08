(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_40 () (_ BitVec 70))
(assert
 (let ((?x6730 ((_ extract 69 54) i_40)))
 (let ((?x2500 ((_ extract 53 0) i_40)))
 (let ((?x212 (concat ?x2500 ?x6730)))
 (let ((?x78 (bvor (bvshl i_40 (bvurem (_ bv18446744073709551616 70) (_ bv70 70))) (bvlshr i_40 (bvsub (_ bv70 70) (bvurem (_ bv18446744073709551616 70) (_ bv70 70)))))))
 (let ((?x471 (ite (and (distinct ?x78 ?x212) true) (_ bv1 1) (_ bv0 1))))
 (not (= ?x471 (_ bv1 1)))))))))
(assert
 (let ((?x6730 ((_ extract 69 54) i_40)))
(let (($x18 (bvsge ?x6730 (_ bv0 16))))
(not $x18))))
(check-sat)
