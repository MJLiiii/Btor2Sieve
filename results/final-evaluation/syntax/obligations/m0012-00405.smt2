(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_40 () (_ BitVec 70))
(assert
 (let ((?x1819 ((_ extract 69 54) i_40)))
 (let ((?x653 ((_ extract 53 0) i_40)))
 (let ((?x6707 (concat ?x653 ?x1819)))
 (let ((?x6953 (bvor (bvshl i_40 (bvurem (_ bv18446744073709551616 70) (_ bv70 70))) (bvlshr i_40 (bvsub (_ bv70 70) (bvurem (_ bv18446744073709551616 70) (_ bv70 70)))))))
 (let ((?x182 (ite (and (distinct ?x6953 ?x6707) true) (_ bv1 1) (_ bv0 1))))
 (not (= ?x182 (_ bv1 1)))))))))
(assert
 (let ((?x1819 ((_ extract 69 54) i_40)))
(let (($x205 (bvule ?x1819 (_ bv32768 16))))
(not $x205))))
(check-sat)
