(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_4 () (_ BitVec 3))
(assert
 true)
(assert
 (let (($x1737 (= i_4 (_ bv4 3))))
(not $x1737)))
(check-sat)
